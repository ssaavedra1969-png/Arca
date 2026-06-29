import uuid
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Date,
    ForeignKey, Text, Boolean, Numeric, Index, UniqueConstraint,
    create_engine, event, Enum as SAEnum
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column,
    relationship, sessionmaker, scoped_session
)

import enum


class Base(DeclarativeBase):
    pass


class EstadoFactura(str, enum.Enum):
    EMITIDA = "EMITIDA"
    ANULADA = "ANULADA"
    ERROR = "ERROR"
    PENDIENTE = "PENDIENTE"
    BORRADOR = "BORRADOR"


class TipoComprobante(int, enum.Enum):
    FACTURA_A = 1
    NOTA_DEBITO_A = 2
    NOTA_CREDITO_A = 3
    FACTURA_B = 6
    NOTA_DEBITO_B = 7
    NOTA_CREDITO_B = 8
    FACTURA_C = 11
    NOTA_DEBITO_C = 12
    NOTA_CREDITO_C = 13
    FACTURA_E = 19
    NOTA_DEBITO_E = 20
    NOTA_CREDITO_E = 21
    FACTURA_M = 51
    NOTA_DEBITO_M = 52
    NOTA_CREDITO_M = 53


class CondicionIVA(int, enum.Enum):
    RESPONSABLE_INSCRIPTO = 1
    RESPONSABLE_NO_INSCRIPTO = 2
    EXENTO = 3
    SUJETO_EXENTO = 4
    CONSUMIDOR_FINAL = 5
    MONOTRIBUTO = 6
    NO_CATEGORIZADO = 7


class Contribuyente(Base):
    __tablename__ = "contribuyentes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cuit: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True)
    razon_social: Mapped[str] = mapped_column(String(250), nullable=False)
    condicion_iva: Mapped[int] = mapped_column(Integer, default=5)
    domicilio: Mapped[Optional[str]] = mapped_column(String(500))
    localidad: Mapped[Optional[str]] = mapped_column(String(100))
    provincia: Mapped[Optional[str]] = mapped_column(String(100))
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(10))
    telefono: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(254))
    categoria_fiscal: Mapped[Optional[str]] = mapped_column(String(50))
    ingresos_brutos: Mapped[Optional[str]] = mapped_column(String(50))
    es_cliente: Mapped[bool] = mapped_column(Boolean, default=True)
    es_proveedor: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    notas: Mapped[Optional[str]] = mapped_column(Text)

    facturas: Mapped[List["Factura"]] = relationship(
        "Factura", back_populates="cliente", foreign_keys="Factura.cliente_id"
    )

    __table_args__ = (
        Index("idx_contribuyente_cuit", "cuit"),
        Index("idx_contribuyente_rs", "razon_social"),
    )


class ProductoServicio(Base):
    __tablename__ = "productos_servicios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="PRODUCTO")
    precio_base: Mapped[float] = mapped_column(Float, default=0.0)
    alicuota_iva: Mapped[float] = mapped_column(Float, default=21.0)
    unidad_medida: Mapped[str] = mapped_column(String(20), default="unidad")
    moneda: Mapped[str] = mapped_column(String(3), default="ARS")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    notas: Mapped[Optional[str]] = mapped_column(Text)

    detalles: Mapped[List["DetalleFactura"]] = relationship(
        "DetalleFactura", back_populates="producto"
    )

    __table_args__ = (
        Index("idx_producto_codigo", "codigo"),
        Index("idx_producto_desc", "descripcion"),
    )


class Factura(Base):
    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    tipo_comprobante: Mapped[int] = mapped_column(Integer, nullable=False)
    punto_venta: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_factura: Mapped[Optional[int]] = mapped_column(Integer)
    cae: Mapped[Optional[str]] = mapped_column(String(14))
    cae_vencimiento: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resultado: Mapped[Optional[str]] = mapped_column(String(20))
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    fecha_vencimiento_pago: Mapped[Optional[Date]] = mapped_column(Date)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("contribuyentes.id"))
    cuit_cliente: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    razon_social_cliente: Mapped[str] = mapped_column(String(250))
    condicion_iva_cliente: Mapped[int] = mapped_column(Integer, default=5)
    domicilio_cliente: Mapped[Optional[str]] = mapped_column(String(500))
    concepto: Mapped[str] = mapped_column(String(20), default="PRODUCTOS")

    moneda: Mapped[str] = mapped_column(String(3), default="ARS")
    cotizacion: Mapped[float] = mapped_column(Float, default=1.0)

    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    iva_total: Mapped[float] = mapped_column(Float, default=0.0)
    percepcion_iibb: Mapped[float] = mapped_column(Float, default=0.0)
    percepcion_iva: Mapped[float] = mapped_column(Float, default=0.0)
    otros_impuestos: Mapped[float] = mapped_column(Float, default=0.0)
    bonificacion: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)

    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default=EstadoFactura.BORRADOR.value)
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(Text)
    factura_origen_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("facturas.id"))
    cae_original: Mapped[Optional[str]] = mapped_column(String(14))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_code: Mapped[Optional[str]] = mapped_column(String(20))
    xml_request: Mapped[Optional[Text]] = mapped_column(Text)
    xml_response: Mapped[Optional[Text]] = mapped_column(Text)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    sync_status: Mapped[str] = mapped_column(String(20), default="LOCAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    cliente: Mapped["Contribuyente"] = relationship(
        "Contribuyente", back_populates="facturas", foreign_keys=[cliente_id]
    )
    detalles: Mapped[List["DetalleFactura"]] = relationship(
        "DetalleFactura", back_populates="factura",
        cascade="all, delete-orphan"
    )
    factura_origen: Mapped[Optional["Factura"]] = relationship(
        "Factura", remote_side=[id], foreign_keys=[factura_origen_id]
    )

    __table_args__ = (
        Index("idx_factura_fecha", "fecha_emision"),
        Index("idx_factura_cae", "cae"),
        Index("idx_factura_cuit_fecha", "cuit_cliente", "fecha_emision"),
        Index("idx_factura_tipo_estado", "tipo_comprobante", "estado"),
        Index("idx_factura_pv_numero", "punto_venta", "numero_factura"),
    )


class DetalleFactura(Base):
    __tablename__ = "detalles_factura"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(Integer, ForeignKey("facturas.id", ondelete="CASCADE"), nullable=False)
    producto_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("productos_servicios.id"))
    codigo_producto: Mapped[Optional[str]] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    cantidad: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unidad_medida: Mapped[str] = mapped_column(String(20), default="unidad")
    precio_unitario: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    alicuota_iva: Mapped[float] = mapped_column(Float, default=21.0)
    importe_iva: Mapped[float] = mapped_column(Float, default=0.0)
    bonificacion: Mapped[float] = mapped_column(Float, default=0.0)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    orden: Mapped[int] = mapped_column(Integer, default=0)

    factura: Mapped["Factura"] = relationship("Factura", back_populates="detalles")
    producto: Mapped[Optional["ProductoServicio"]] = relationship(
        "ProductoServicio", back_populates="detalles"
    )


class TokenWSAA(Base):
    __tablename__ = "tokens_wsaa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(50), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    sign: Mapped[str] = mapped_column(Text, nullable=False)
    expiration_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    generation_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False)
    certificate_hash: Mapped[str] = mapped_column(String(64))
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_token_service", "service"),
        Index("idx_token_expiration", "expiration_time"),
    )


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    usuario: Mapped[str] = mapped_column(String(100), default="system")
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad: Mapped[Optional[str]] = mapped_column(String(50))
    entidad_id: Mapped[Optional[int]] = mapped_column(Integer)
    detalle: Mapped[Optional[str]] = mapped_column(Text)
    ip_origen: Mapped[Optional[str]] = mapped_column(String(50))
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    nivel: Mapped[str] = mapped_column(String(20), default="INFO")

    __table_args__ = (
        Index("idx_audit_timestamp_accion", "timestamp", "accion"),
    )


class Configuracion(Base):
    __tablename__ = "configuracion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(String(50), default="general")
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))
    encriptado: Mapped[bool] = mapped_column(Boolean, default=False)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    checksum: Mapped[Optional[str]] = mapped_column(String(64))
    tipo: Mapped[str] = mapped_column(String(20), default="AUTOMATICO")
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    restaurado: Mapped[Optional[datetime]] = mapped_column(DateTime)


def enable_wal_mode(conn, record):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA busy_timeout=5000")


def init_db(db_path: str) -> scoped_session:
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    event.listen(engine, "connect", enable_wal_mode)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    return Session


def get_session_factory(db_path: str):
    return init_db(db_path)
