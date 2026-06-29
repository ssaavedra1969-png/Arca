from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal


class DetalleFacturaModel(BaseModel):
    codigo_producto: Optional[str] = None
    descripcion: str = Field(..., min_length=1, max_length=500)
    cantidad: float = Field(..., gt=0)
    unidad_medida: str = "unidad"
    precio_unitario: float = Field(..., ge=0)
    alicuota_iva: float = Field(default=21.0, ge=0, le=100)
    bonificacion: float = Field(default=0.0, ge=0)

    @field_validator("cantidad")
    def validar_cantidad(cls, v):
        if v > 999999999.99:
            raise ValueError("Cantidad demasiado grande")
        return round(v, 4)

    @field_validator("precio_unitario")
    def validar_precio(cls, v):
        if v > 9999999999.99:
            raise ValueError("Precio unitario demasiado grande")
        return round(v, 2)

    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.precio_unitario - self.bonificacion, 2)

    @property
    def importe_iva(self) -> float:
        return round(self.subtotal * self.alicuota_iva / 100, 2)


class FacturaModel(BaseModel):
    tipo_comprobante: int = Field(..., ge=1, le=99)
    punto_venta: int = Field(..., ge=1, le=9999)
    cliente_id: Optional[int] = None
    cuit_cliente: str = Field(..., min_length=11, max_length=13)
    razon_social_cliente: str = Field(..., min_length=1, max_length=250)
    condicion_iva_cliente: int = Field(default=5, ge=1, le=14)
    domicilio_cliente: Optional[str] = None
    concepto: str = Field(default="PRODUCTOS", pattern="^(PRODUCTOS|SERVICIOS|PRODUCTOS Y SERVICIOS)$")
    moneda: str = Field(default="ARS", min_length=3, max_length=3)
    cotizacion: float = Field(default=1.0, ge=0.0001)
    fecha_emision: Optional[date] = None
    fecha_vencimiento_pago: Optional[date] = None
    detalles: List[DetalleFacturaModel] = Field(..., min_length=1)
    percepcion_iibb: float = Field(default=0.0, ge=0)
    percepcion_iva: float = Field(default=0.0, ge=0)
    otros_impuestos: float = Field(default=0.0, ge=0)
    bonificacion: float = Field(default=0.0, ge=0)
    observaciones: Optional[str] = None
    cae_original: Optional[str] = None
    factura_origen_id: Optional[int] = None

    @field_validator("cuit_cliente")
    def validar_cuit(cls, v):
        from utils.validators import ARCAValidators
        valido, msg = ARCAValidators.validar_cuit(v)
        if not valido:
            raise ValueError(f"CUIT invalido: {msg}")
        return v.replace("-", "")

    @field_validator("tipo_comprobante")
    def validar_tipo(cls, v):
        TIPOS_VALIDOS = {1, 2, 3, 6, 7, 8, 11, 12, 13, 19, 20, 21, 51, 52, 53}
        if v not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo de comprobante invalido: {v}")
        return v

    def calcular_totales(self) -> Dict[str, float]:
        subtotal = sum(d.subtotal for d in self.detalles)
        iva_total = sum(d.importe_iva for d in self.detalles)
        total = subtotal + iva_total + self.percepcion_iibb + self.percepcion_iva + self.otros_impuestos - self.bonificacion
        return {
            "subtotal": round(subtotal, 2),
            "iva_total": round(iva_total, 2),
            "total": round(total, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump(exclude={"detalles"})
        data["detalles"] = [d.model_dump() for d in self.detalles]
        return data


class ResultadoFactura(BaseModel):
    success: bool
    cae: Optional[str] = None
    cae_vencimiento: Optional[datetime] = None
    numero_factura: Optional[int] = None
    resultado: Optional[str] = None
    factura_id: Optional[int] = None
    uuid: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    xml_request: Optional[str] = None
    xml_response: Optional[str] = None
    observaciones: Optional[str] = None


class FiltroBusquedaModel(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    tipo_comprobante: Optional[int] = None
    estado: Optional[str] = None
    cuit_cliente: Optional[str] = None
    razon_social: Optional[str] = None
    punto_venta: Optional[int] = None
    cae: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ClienteModel(BaseModel):
    cuit: str = Field(..., min_length=11, max_length=13)
    razon_social: str = Field(..., min_length=1, max_length=250)
    condicion_iva: int = Field(default=5, ge=1, le=14)
    domicilio: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    categoria_fiscal: Optional[str] = None
    ingresos_brutos: Optional[str] = None
    es_cliente: bool = True
    es_proveedor: bool = False
    notas: Optional[str] = None

    @field_validator("cuit")
    def validar_cuit(cls, v):
        from utils.validators import ARCAValidators
        valido, msg = ARCAValidators.validar_cuit(v)
        if not valido:
            raise ValueError(f"CUIT invalido: {msg}")
        return v.replace("-", "")

    @field_validator("email")
    def validar_email(cls, v):
        if v:
            from utils.validators import ARCAValidators
            valido, msg = ARCAValidators.validar_email(v)
            if not valido:
                raise ValueError(f"Email invalido: {msg}")
        return v


class ProductoModel(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    descripcion: str = Field(..., min_length=1, max_length=500)
    tipo: str = Field(default="PRODUCTO", pattern="^(PRODUCTO|SERVICIO)$")
    precio_base: float = Field(default=0.0, ge=0)
    alicuota_iva: float = Field(default=21.0, ge=0, le=100)
    unidad_medida: str = "unidad"
    moneda: str = "ARS"
    notas: Optional[str] = None


class ConfigModel(BaseModel):
    arca_cuit: str
    arca_punto_venta: int
    arca_cert_file: str
    arca_key_file: str
    arca_homo: bool = False
    arca_cert_pin: Optional[str] = None
    moneda_defecto: str = "ARS"
    app_theme: str = "dark"
