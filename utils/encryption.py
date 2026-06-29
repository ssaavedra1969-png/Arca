import os
import base64
import hashlib
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from loguru import logger


class EncryptionManager:
    _instance = None
    _fernet: Optional[Fernet] = None
    _aes_key: Optional[bytes] = None
    _vault_path: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, master_password: str, vault_path: Optional[Path] = None):
        if vault_path:
            self._vault_path = Path(vault_path)
        else:
            self._vault_path = Path.cwd() / "data" / ".vault"

        self._vault_path.parent.mkdir(parents=True, exist_ok=True)

        salt = self._get_or_create_salt()
        key = self._derive_key(master_password, salt)
        self._fernet = Fernet(base64.urlsafe_b64encode(key[:32]))
        self._aes_key = key[:32]

        logger.debug("Encryption manager initialized")

    def _get_or_create_salt(self) -> bytes:
        salt_file = self._vault_path.parent / ".salt"
        if salt_file.exists():
            with open(salt_file, "rb") as f:
                return f.read()
        salt = os.urandom(32)
        with open(salt_file, "wb") as f:
            f.write(salt)
        return salt

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=2**14,
            r=8,
            p=1,
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))

    def encrypt(self, data: str) -> str:
        if not self._fernet:
            raise RuntimeError("EncryptionManager no inicializado")
        return self._fernet.encrypt(data.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_data: str) -> str:
        if not self._fernet:
            raise RuntimeError("EncryptionManager no inicializado")
        return self._fernet.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")

    def encrypt_aes_gcm(self, data: str, aad: Optional[bytes] = None) -> Tuple[bytes, bytes, bytes]:
        if not self._aes_key:
            raise RuntimeError("EncryptionManager no inicializado")
        aesgcm = AESGCM(self._aes_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), aad or b"")
        return nonce, ciphertext, aad or b""

    def decrypt_aes_gcm(self, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> str:
        if not self._aes_key:
            raise RuntimeError("EncryptionManager no inicializado")
        aesgcm = AESGCM(self._aes_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext.decode("utf-8")

    def verify_password(self, password: str, stored_hash: str) -> bool:
        salt = base64.b64decode(stored_hash[:44])
        stored = stored_hash[44:]
        key = self._derive_key(password, salt)
        new_hash = base64.b64encode(key).decode()
        return new_hash == stored

    def hash_password(self, password: str) -> str:
        salt = os.urandom(32)
        key = self._derive_key(password, salt)
        return base64.b64encode(salt).decode() + base64.b64encode(key).decode()


class CredentialVault:
    def __init__(self, encryption_manager: EncryptionManager):
        self.enc = encryption_manager
        self._vault_file = Path.cwd() / "data" / ".vault" / "credentials.enc"
        self._vault_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, str] = {}

    def save_credential(self, key: str, value: str):
        encrypted = self.enc.encrypt(value)
        self._load_vault()
        self._cache[key] = encrypted
        self._save_vault()
        logger.info(f"Credential '{key}' saved securely")

    def get_credential(self, key: str) -> Optional[str]:
        self._load_vault()
        encrypted = self._cache.get(key)
        if encrypted:
            return self.enc.decrypt(encrypted)
        return None

    def delete_credential(self, key: str):
        self._load_vault()
        self._cache.pop(key, None)
        self._save_vault()

    def list_keys(self) -> list:
        self._load_vault()
        return list(self._cache.keys())

    def _load_vault(self):
        if self._vault_file.exists():
            try:
                with open(self._vault_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    import json
                    self._cache = json.loads(content)
            except Exception as e:
                logger.error(f"Error loading vault: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def _save_vault(self):
        import json
        try:
            with open(self._vault_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving vault: {e}")

    def clear_cache(self):
        self._cache = {}


def verify_certificate_integrity(cert_path: Path, key_path: Path) -> Tuple[bool, str]:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization, hashes

        with open(cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())

        with open(key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)

        cert_public_key = cert.public_key()
        key_public_key = key.public_key()

        if cert_public_key != key_public_key:
            return False, "La clave privada no coincide con el certificado"

        now = datetime.utcnow()
        if now < cert.not_valid_before_utc:
            return False, f"El certificado aun no es valido (valido desde {cert.not_valid_before_utc})"
        if now > cert.not_valid_after_utc:
            return False, f"El certificado ha expirado (vencio el {cert.not_valid_after_utc})"

        fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        return True, fingerprint

    except Exception as e:
        return False, f"Error verificando certificado: {e}"


from datetime import datetime
