import pytest
from datetime import datetime
from database.models import (
    Contribuyente, Factura, DetalleFactura, ProductoServicio,
    TokenWSAA, EstadoFactura, TipoComprobante
)


class TestContribuyenteModel:
    def test_crear_contribuyente(self, db_session):
        c = Contribuyente(
            cuit="20345678901",
            razon_social="Test SA",
            condicion_iva=1,
            activo=True,
        )
        db_session.add(c)
        db_session.flush()
        assert c.id is not None
        assert c.cuit == "20345678901"
        assert c.creado is not None

    def test_contribuyente_defaults(self, db_session):
        c = Contribuyente(
            cuit="27345678905",
            razon_social="Test 2 SA",
        )
        db_session.add(c)
        db_session.flush()
        assert c.condicion_iva == 5
        assert c.es_cliente is True
        assert c.es_proveedor is False
        assert c.activo is True

    def test_cuit_unico(self, db_session):
        c1 = Contribuyente(cuit="20345678901", razon_social="A")
        db_session.add(c1)
        db_session.flush()
        c2 = Contribuyente(cuit="20345678901", razon_social="B")
        db_session.add(c2)
        with pytest.raises(Exception):
            db_session.flush()


class TestFacturaModel:
    def test_crear_factura(self, db_session, cliente_ejemplo):
        f = Factura(
            tipo_comprobante=TipoComprobante.FACTURA_C.value,
            punto_venta=1,
            fecha_emision=datetime.now(),
            cliente_id=cliente_ejemplo.id,
            cuit_cliente=cliente_ejemplo.cuit,
            razon_social_cliente=cliente_ejemplo.razon_social,
            concepto="PRODUCTOS",
            moneda="ARS",
            subtotal=1000.0,
            iva_total=210.0,
            total=1210.0,
            estado=EstadoFactura.BORRADOR.value,
        )
        db_session.add(f)
        db_session.flush()
        assert f.id is not None
        assert f.uuid is not None
        assert f.estado == "BORRADOR"

    def test_factura_con_detalles(self, db_session, cliente_ejemplo, producto_ejemplo):
        f = Factura(
            tipo_comprobante=11,
            punto_venta=1,
            fecha_emision=datetime.now(),
            cliente_id=cliente_ejemplo.id,
            cuit_cliente=cliente_ejemplo.cuit,
            razon_social_cliente=cliente_ejemplo.razon_social,
            concepto="PRODUCTOS",
            moneda="ARS",
            subtotal=2000.0,
            iva_total=420.0,
            total=2420.0,
            estado="EMITIDA",
        )
        db_session.add(f)
        db_session.flush()

        d = DetalleFactura(
            factura_id=f.id,
            producto_id=producto_ejemplo.id,
            descripcion=producto_ejemplo.descripcion,
            cantidad=2.0,
            precio_unitario=1000.0,
            alicuota_iva=21.0,
            importe_iva=420.0,
            subtotal=2000.0,
        )
        db_session.add(d)
        db_session.flush()

        assert len(f.detalles) == 1
        assert f.detalles[0].descripcion == "Producto de Prueba"
        assert f.detalles[0].subtotal == 2000.0


class TestProductoModel:
    def test_crear_producto(self, db_session):
        p = ProductoServicio(
            codigo="TEST-001",
            descripcion="Producto Test",
            precio_base=500.0,
            alicuota_iva=21.0,
        )
        db_session.add(p)
        db_session.flush()
        assert p.id is not None
        assert p.tipo == "PRODUCTO"

    def test_codigo_unico(self, db_session):
        p1 = ProductoServicio(codigo="TEST-001", descripcion="A")
        db_session.add(p1)
        db_session.flush()
        p2 = ProductoServicio(codigo="TEST-001", descripcion="B")
        db_session.add(p2)
        with pytest.raises(Exception):
            db_session.flush()


class TestTokenWSAA:
    def test_crear_token(self, db_session):
        t = TokenWSAA(
            service="wsfe",
            token="token123",
            sign="sign123",
            expiration_time=datetime(2026, 12, 31),
            cuit="20345678901",
        )
        db_session.add(t)
        db_session.flush()
        assert t.id is not None
