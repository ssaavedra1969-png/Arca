import pytest
from pydantic import ValidationError
from core.models import FacturaModel, ClienteModel, DetalleFacturaModel


class TestDetalleFacturaModel:
    def test_detalle_valido(self):
        d = DetalleFacturaModel(
            descripcion="Producto Test",
            cantidad=2.0,
            precio_unitario=100.0,
            alicuota_iva=21.0,
        )
        assert d.subtotal == 200.0
        assert d.importe_iva == 42.0

    def test_cantidad_invalida(self):
        with pytest.raises(ValidationError):
            DetalleFacturaModel(
                descripcion="Test",
                cantidad=0,
                precio_unitario=100,
            )

    def test_precio_negativo(self):
        with pytest.raises(ValidationError):
            DetalleFacturaModel(
                descripcion="Test",
                cantidad=1,
                precio_unitario=-10,
            )


class TestFacturaModel:
    def test_factura_valida(self):
        f = FacturaModel(
            tipo_comprobante=11,
            punto_venta=1,
            cuit_cliente="20345678901",
            razon_social_cliente="Cliente Test SA",
            condicion_iva_cliente=5,
            detalles=[
                DetalleFacturaModel(
                    descripcion="Item 1",
                    cantidad=1,
                    precio_unitario=1000.0,
                    alicuota_iva=21.0,
                )
            ],
        )
        totales = f.calcular_totales()
        assert totales["subtotal"] == 1000.0
        assert totales["iva_total"] == 210.0
        assert totales["total"] == 1210.0

    def test_cuit_invalido(self):
        with pytest.raises(ValidationError):
            FacturaModel(
                tipo_comprobante=11,
                punto_venta=1,
                cuit_cliente="12345678901",
                razon_social_cliente="Test",
                detalles=[
                    DetalleFacturaModel(
                        descripcion="Item", cantidad=1, precio_unitario=100
                    )
                ],
            )

    def test_tipo_invalido(self):
        with pytest.raises(ValidationError):
            FacturaModel(
                tipo_comprobante=99,
                punto_venta=1,
                cuit_cliente="20345678901",
                razon_social_cliente="Test",
                detalles=[],
            )

    def test_sin_detalles(self):
        with pytest.raises(ValidationError):
            FacturaModel(
                tipo_comprobante=11,
                punto_venta=1,
                cuit_cliente="20345678901",
                razon_social_cliente="Test",
                detalles=[],
            )


class TestClienteModel:
    def test_cliente_valido(self):
        c = ClienteModel(
            cuit="20345678901",
            razon_social="Cliente SA",
            condicion_iva=1,
        )
        assert c.cuit == "20345678901"

    def test_cuit_invalido(self):
        with pytest.raises(ValidationError):
            ClienteModel(
                cuit="11111111111",
                razon_social="Test",
            )
