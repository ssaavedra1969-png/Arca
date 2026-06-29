import pytest
from datetime import datetime, date, timedelta
from database.repositories import (
    ContribuyenteRepository, ProductoRepository,
    FacturaRepository, TokenRepository, ConfiguracionRepository
)
from database.models import EstadoFactura


class TestContribuyenteRepository:
    def test_create_and_get(self, db_session):
        repo = ContribuyenteRepository(db_session)
        c = repo.create({
            "cuit": "20345678901",
            "razon_social": "Test SA",
            "condicion_iva": 1,
        })
        assert c.id is not None
        assert c.cuit == "20345678901"

        retrieved = repo.get_by_id(c.id)
        assert retrieved is not None
        assert retrieved.razon_social == "Test SA"

        by_cuit = repo.get_by_cuit("20345678901")
        assert by_cuit is not None

    def test_search(self, db_session):
        repo = ContribuyenteRepository(db_session)
        repo.create({"cuit": "20345678901", "razon_social": "Cliente Alpha SA"})
        repo.create({"cuit": "27345678905", "razon_social": "Beta Corp SA"})

        results = repo.search("Alpha")
        assert len(results) == 1
        assert results[0].razon_social == "Cliente Alpha SA"

        results = repo.search("3456789")
        assert len(results) == 2

    def test_update(self, db_session):
        repo = ContribuyenteRepository(db_session)
        c = repo.create({"cuit": "20345678901", "razon_social": "Viejo Nombre"})

        repo.update(c.id, {"razon_social": "Nuevo Nombre"})
        updated = repo.get_by_id(c.id)
        assert updated.razon_social == "Nuevo Nombre"


class TestFacturaRepository:
    def test_create_with_detalles(self, db_session, cliente_ejemplo):
        repo = FacturaRepository(db_session)
        data = {
            "tipo_comprobante": 11,
            "punto_venta": 1,
            "cliente_id": cliente_ejemplo.id,
            "cuit_cliente": cliente_ejemplo.cuit,
            "razon_social_cliente": cliente_ejemplo.razon_social,
            "condicion_iva_cliente": 5,
            "concepto": "PRODUCTOS",
            "moneda": "ARS",
            "estado": EstadoFactura.EMITIDA.value,
        }
        detalles = [
            {
                "descripcion": "Item 1",
                "cantidad": 2.0,
                "precio_unitario": 100.0,
                "alicuota_iva": 21.0,
            },
            {
                "descripcion": "Item 2",
                "cantidad": 1.0,
                "precio_unitario": 500.0,
                "alicuota_iva": 10.5,
            },
        ]
        factura = repo.create(data, detalles)
        assert factura.id is not None
        assert len(factura.detalles) == 2

    def test_get_ultimo_numero(self, db_session, cliente_ejemplo):
        repo = FacturaRepository(db_session)
        numero = repo.get_ultimo_numero(1, 11)
        assert numero == 0

        for i in range(1, 4):
            repo.create({
                "tipo_comprobante": 11,
                "punto_venta": 1,
                "numero_factura": i,
                "cliente_id": cliente_ejemplo.id,
                "cuit_cliente": cliente_ejemplo.cuit,
                "razon_social_cliente": cliente_ejemplo.razon_social,
                "concepto": "PRODUCTOS",
                "moneda": "ARS",
                "estado": EstadoFactura.EMITIDA.value,
            }, [{"descripcion": f"Item {i}", "cantidad": 1, "precio_unitario": 100.0, "alicuota_iva": 21.0}])

        numero = repo.get_ultimo_numero(1, 11)
        assert numero == 3

    def test_get_estadisticas(self, db_session, cliente_ejemplo):
        repo = FacturaRepository(db_session)
        for i in range(5):
            repo.create({
                "tipo_comprobante": 11,
                "punto_venta": 1,
                "cliente_id": cliente_ejemplo.id,
                "cuit_cliente": cliente_ejemplo.cuit,
                "razon_social_cliente": cliente_ejemplo.razon_social,
                "concepto": "PRODUCTOS",
                "moneda": "ARS",
                "subtotal": 1000.0,
                "iva_total": 210.0,
                "total": 1210.0,
                "estado": EstadoFactura.EMITIDA.value,
            }, [{"descripcion": "Item", "cantidad": 1, "precio_unitario": 1000.0, "alicuota_iva": 21.0}])

        stats = repo.get_estadisticas()
        assert stats["cantidad_facturas"] >= 5
        assert stats["total_facturado"] >= 1210.0 * 5


class TestConfiguracionRepository:
    def test_set_and_get(self, db_session):
        repo = ConfiguracionRepository(db_session)
        repo.set("test_key", "test_value", "testing")
        valor = repo.get("test_key")
        assert valor == "test_value"

        valor2 = repo.get("nonexistent", "default")
        assert valor2 == "default"

    def test_get_categoria(self, db_session):
        repo = ConfiguracionRepository(db_session)
        repo.set("k1", "v1", "cat1")
        repo.set("k2", "v2", "cat1")
        repo.set("k3", "v3", "cat2")

        cat1 = repo.get_categoria("cat1")
        assert "k1" in cat1
        assert "k2" in cat1
        assert "k3" not in cat1
