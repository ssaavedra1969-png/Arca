from typing import Optional, Dict, Any


class ARCAError(Exception):
    codigo: str = "ERR-0000"
    mensaje_usuario: str = "Error interno del sistema"
    http_status: int = 500
    detalle: Optional[str] = None
    datos_extra: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        mensaje: str = "",
        detalle: Optional[str] = None,
        datos_extra: Optional[Dict[str, Any]] = None,
        causa: Optional[Exception] = None,
    ):
        self.mensaje = mensaje or self.mensaje_usuario
        self.detalle = detalle
        self.datos_extra = datos_extra
        self.causa = causa
        super().__init__(self.mensaje)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "detalle": self.detalle,
            "datos_extra": self.datos_extra or {},
        }


class AuthError(ARCAError):
    codigo = "ERR-1000"
    mensaje_usuario = "Error de autenticacion en ARCA"
    http_status = 401


class CertError(AuthError):
    codigo = "ERR-1001"
    mensaje_usuario = "Error en el certificado digital"


class TokenExpiredError(AuthError):
    codigo = "ERR-1002"
    mensaje_usuario = "El token de acceso ha expirado"


class ConnectionError(ARCAError):
    codigo = "ERR-2000"
    mensaje_usuario = "Error de conexion con ARCA"
    http_status = 503


class TimeoutError(ConnectionError):
    codigo = "ERR-2001"
    mensaje_usuario = "Tiempo de espera agotado al conectar con ARCA"


class ValidationError(ARCAError):
    codigo = "ERR-3000"
    mensaje_usuario = "Datos invalidos"
    http_status = 422


class CUITError(ValidationError):
    codigo = "ERR-3001"
    mensaje_usuario = "CUIT invalido"


class BusinessError(ARCAError):
    codigo = "ERR-4000"
    mensaje_usuario = "Error de regla de negocio de ARCA"
    http_status = 422


class ComprobanteError(BusinessError):
    codigo = "ERR-4001"
    mensaje_usuario = "Error en el comprobante"


class CAEError(BusinessError):
    codigo = "ERR-4002"
    mensaje_usuario = "Error en el CAE del comprobante"


class DatabaseError(ARCAError):
    codigo = "ERR-5000"
    mensaje_usuario = "Error en la base de datos"
    http_status = 500


class IntegrityError(DatabaseError):
    codigo = "ERR-5001"
    mensaje_usuario = "Error de integridad en la base de datos"


class ConfigError(ARCAError):
    codigo = "ERR-6000"
    mensaje_usuario = "Error de configuracion"
    http_status = 500


class VaultError(ARCAError):
    codigo = "ERR-7000"
    mensaje_usuario = "Error en la boveda de credenciales"
    http_status = 500


class SyncError(ARCAError):
    codigo = "ERR-8000"
    mensaje_usuario = "Error de sincronizacion con ARCA"
    http_status = 503


class OfflineQueueError(ARCAError):
    codigo = "ERR-8001"
    mensaje_usuario = "Error en la cola de facturas pendientes"
