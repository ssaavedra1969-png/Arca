import os
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID
from loguru import logger
from config import ConfigManager
from database.models import TokenWSAA, get_session_factory
from database.repositories import TokenRepository
from utils.exceptions import AuthError, CertError, TokenExpiredError


class CertificateManager:
    def __init__(self, cert_path: Path, key_path: Path, pin: Optional[str] = None):
        self.cert_path = Path(cert_path)
        self.key_path = Path(key_path)
        self.pin = pin
        self._cert = None
        self._key = None
        self._fingerprint = None

    def load(self) -> Tuple[bool, str]:
        try:
            if not self.cert_path.exists():
                return False, f"Certificado no encontrado: {self.cert_path}"
            if not self.key_path.exists():
                return False, f"Clave privada no encontrada: {self.key_path}"

            with open(self.cert_path, "rb") as f:
                cert_data = f.read()
            self._cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            with open(self.key_path, "rb") as f:
                key_data = f.read()
            password = self.pin.encode() if self.pin else None
            self._key = serialization.load_pem_private_key(
                key_data, password=password, backend=default_backend()
            )

            cert_pub = self._cert.public_key()
            key_pub = self._key.public_key()
            if cert_pub != key_pub:
                return False, "La clave privada no coincide con el certificado"

            self._fingerprint = self._cert.fingerprint(hashes.SHA256()).hex()
            return True, self._fingerprint

        except Exception as e:
            return False, f"Error cargando certificado: {e}"

    def validate(self) -> Tuple[bool, str]:
        if not self._cert:
            ok, msg = self.load()
            if not ok:
                return False, msg

        now = datetime.utcnow()
        if now < self._cert.not_valid_before_utc:
            return False, f"Certificado no valido hasta {self._cert.not_valid_before_utc}"
        if now > self._cert.not_valid_after_utc:
            return False, f"Certificado expirado el {self._cert.not_valid_after_utc}"

        if self._fingerprint:
            actual_hash = self._cert.fingerprint(hashes.SHA256()).hex()
            if actual_hash != self._fingerprint:
                return False, "Huella digital del certificado alterada"

        return True, "Certificado valido"

    def get_info(self) -> Dict[str, Any]:
        if not self._cert:
            return {"error": "Certificado no cargado"}

        try:
            subject = self._cert.subject
            issuer = self._cert.issuer
            cn = subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            org = subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)

            return {
                "subject": str(cn[0].value) if cn else "N/A",
                "organization": str(org[0].value) if org else "N/A",
                "issuer": str(issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value),
                "valid_from": self._cert.not_valid_before_utc,
                "valid_until": self._cert.not_valid_after_utc,
                "days_remaining": (self._cert.not_valid_after_utc - datetime.utcnow()).days,
                "serial": self._cert.serial_number,
                "fingerprint_sha256": self._fingerprint or "",
                "signature_algorithm": self._cert.signature_algorithm_oid._name,
            }
        except Exception as e:
            return {"error": str(e)}

    def is_expiring_soon(self, days: int = 7) -> bool:
        if not self._cert:
            return False
        remaining = (self._cert.not_valid_after_utc - datetime.utcnow()).days
        return remaining <= days

    def get_cuit_from_cert(self) -> Optional[str]:
        if not self._cert:
            return None
        try:
            cn = self._cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if cn:
                value = cn[0].value
                import re
                match = re.search(r'\b(20|23|24|27|30|33|34)\d{9}\b', value)
                if match:
                    return match.group(0)
            serial = str(self._cert.serial_number)
            match = re.search(r'\b(20|23|24|27|30|33|34)\d{9}\b', serial)
            if match:
                return match.group(0)
            return None
        except Exception:
            return None


class TokenManager:
    def __init__(self, session_factory, enc_manager=None):
        self.session_factory = session_factory
        self.enc_manager = enc_manager
        self._token_cache: Dict[str, Tuple[str, str, datetime]] = {}

    def get_token(self, service: str, cuit: str, cert_manager: CertificateManager) -> Tuple[str, str]:
        cached = self._get_cached(service, cuit)
        if cached:
            logger.debug(f"Token en memoria para {service}")
            return cached

        db_token = self._get_from_db(service, cuit)
        if db_token:
            self._token_cache[f"{service}:{cuit}"] = (
                db_token.token, db_token.sign, db_token.expiration_time
            )
            logger.debug(f"Token desde DB para {service}")
            return db_token.token, db_token.sign

        return self._fetch_new_token(service, cuit, cert_manager)

    def _get_cached(self, service: str, cuit: str) -> Optional[Tuple[str, str]]:
        key = f"{service}:{cuit}"
        if key in self._token_cache:
            token, sign, exp = self._token_cache[key]
            if exp > datetime.utcnow() + timedelta(minutes=5):
                return token, sign
            del self._token_cache[key]
        return None

    def _get_from_db(self, service: str, cuit: str) -> Optional[TokenWSAA]:
        session = self.session_factory()
        try:
            repo = TokenRepository(session)
            token = repo.get_valid_token(service, cuit)
            return token
        finally:
            session.close()

    def _fetch_new_token(self, service: str, cuit: str, cert_manager: CertificateManager) -> Tuple[str, str]:
        import requests
        from pyafipws.wsaa import WSAA

        try:
            settings = ConfigManager.get_settings()
            wsaa = WSAA()
            wsaa.Conectar(settings.get_wsaa_url(), settings.arca_timeout_connect)

            cms = wsaa.CreateTRA(service, ttl=12 * 60 * 60)
            cms_firmado = wsaa.SignTRA(cms, str(cert_manager.cert_path), str(cert_manager.key_path))

            wsaa.LoginCMS(cms_firmado)
            token = wsaa.Token
            sign = wsaa.Sign

            if not token or not sign:
                raise AuthError("WSAA no devolvio token o sign")

            expiration = datetime.utcnow() + timedelta(hours=11)

            session = self.session_factory()
            try:
                repo = TokenRepository(session)
                repo.save_token(
                    service=service,
                    token=token,
                    sign=sign,
                    expiration_time=expiration,
                    cuit=cuit,
                    cert_hash=cert_manager._fingerprint or "",
                )
                session.commit()
            finally:
                session.close()

            self._token_cache[f"{service}:{cuit}"] = (token, sign, expiration)
            logger.info(f"Token WSAA obtenido para {service}, expira {expiration}")
            return token, sign

        except requests.exceptions.ConnectTimeout:
            raise AuthError("Tiempo de espera agotado conectando con WSAA")
        except requests.exceptions.ConnectionError:
            raise AuthError("No se pudo conectar con WSAA. Verifique la conexion a internet")
        except Exception as e:
            raise AuthError(f"Error obteniendo token WSAA: {e}")


class Authenticator:
    def __init__(self, settings=None):
        self.settings = settings or ConfigManager.get_settings()
        self.cert_manager: Optional[CertificateManager] = None
        self.token_manager: Optional[TokenManager] = None
        self.session_factory = None
        self._initialized = False

    def initialize(self, session_factory=None, enc_manager=None):
        cert_path = self.settings.get_cert_path()
        key_path = self.settings.get_key_path()

        self.cert_manager = CertificateManager(
            cert_path, key_path, self.settings.arca_cert_pin or None
        )

        ok, msg = self.cert_manager.load()
        if not ok:
            raise CertError(f"Error cargando certificado: {msg}")

        logger.info(f"Certificado cargado correctamente. Fingerprint: {msg[:16]}...")

        self.session_factory = session_factory or get_session_factory(
            str(self.settings.get_db_path())
        )
        self.token_manager = TokenManager(self.session_factory, enc_manager)
        self._initialized = True

    def authenticate(self, service: str = "wsfe") -> Tuple[str, str]:
        if not self._initialized:
            raise AuthError("Authenticator no inicializado")

        ok, msg = self.cert_manager.validate()
        if not ok:
            raise CertError(f"Certificado invalido: {msg}")

        cuit = self.cert_manager.get_cuit_from_cert()
        if not cuit:
            cuit = str(self.settings.arca_cuit)

        return self.token_manager.get_token(service, cuit, self.cert_manager)

    def get_cert_info(self) -> Dict[str, Any]:
        if not self.cert_manager:
            return {}
        return self.cert_manager.get_info()

    def get_cuit(self) -> str:
        if self.cert_manager:
            cuit = self.cert_manager.get_cuit_from_cert()
            if cuit:
                return cuit
        return str(self.settings.arca_cuit)

    def is_cert_expiring_soon(self, days: int = 7) -> bool:
        if self.cert_manager:
            return self.cert_manager.is_expiring_soon(days)
        return False

    def test_connection(self) -> Tuple[bool, str]:
        try:
            token, sign = self.authenticate()
            if token and sign:
                return True, "Conexion exitosa con ARCA"
            return False, "No se pudo obtener token"
        except AuthError as e:
            return False, f"Error de autenticacion: {e.mensaje}"
        except CertError as e:
            return False, f"Error de certificado: {e.mensaje}"
        except Exception as e:
            return False, f"Error de conexion: {e}"
