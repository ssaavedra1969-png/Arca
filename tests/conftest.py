import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime, date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session

from database.models import Base, enable_wal_mode, Contribuyente, ProductoServicio, Factura, DetalleFactura
from config import ConfigManager


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", enable_wal_mode)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = scoped_session(sessionmaker(bind=connection))
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def settings():
    return ConfigManager.load()


@pytest.fixture
def cliente_ejemplo(db_session):
    c = Contribuyente(
        cuit="20345678901",
        razon_social="Cliente Ejemplo SA",
        condicion_iva=1,
        domicilio="Av. Siempre Viva 123",
        activo=True,
    )
    db_session.add(c)
    db_session.flush()
    return c


@pytest.fixture
def producto_ejemplo(db_session):
    p = ProductoServicio(
        codigo="PROD-001",
        descripcion="Producto de Prueba",
        precio_base=1000.0,
        alicuota_iva=21.0,
        activo=True,
    )
    db_session.add(p)
    db_session.flush()
    return p


@pytest.fixture
def factura_ejemplo(db_session, cliente_ejemplo):
    f = Factura(
        uuid="test-uuid-1234",
        tipo_comprobante=11,
        punto_venta=1,
        numero_factura=1,
        cae="12345678901234",
        cae_vencimiento=datetime(2026, 12, 31),
        resultado="A",
        fecha_emision=datetime.now(),
        cliente_id=cliente_ejemplo.id,
        cuit_cliente=cliente_ejemplo.cuit,
        razon_social_cliente=cliente_ejemplo.razon_social,
        condicion_iva_cliente=cliente_ejemplo.condicion_iva,
        concepto="PRODUCTOS",
        moneda="ARS",
        cotizacion=1.0,
        subtotal=1000.0,
        iva_total=210.0,
        total=1210.0,
        estado="EMITIDA",
    )
    db_session.add(f)
    db_session.flush()

    d = DetalleFactura(
        factura_id=f.id,
        producto_id=1,
        descripcion="Producto de Prueba",
        cantidad=1.0,
        precio_unitario=1000.0,
        alicuota_iva=21.0,
        importe_iva=210.0,
        subtotal=1000.0,
    )
    db_session.add(d)
    db_session.flush()
    return f
