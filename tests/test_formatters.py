import pytest
from datetime import datetime, date
from utils.formatters import Formatters


class TestFormatearImporte:
    def test_pesos(self):
        result = Formatters.formatear_importe(1234.56)
        assert "1.234" in result
        assert "56" in result

    def test_cero(self):
        result = Formatters.formatear_importe(0)
        assert "0" in result

    def test_entero(self):
        result = Formatters.formatear_importe(1000)
        assert "1.000" in result


class TestFormatearCUIT:
    def test_con_formato(self):
        result = Formatters.formatear_cuit("20345678901")
        assert result == "20-34567890-1"

    def test_ya_formateado(self):
        result = Formatters.formatear_cuit("20-34567890-1")
        assert result == "20-34567890-1"

    def test_numero(self):
        result = Formatters.formatear_cuit(20345678901)
        assert result == "20-34567890-1"


class TestFormatearFecha:
    def test_date_object(self):
        result = Formatters.formatear_fecha(date(2026, 1, 15))
        assert result == "15/01/2026"

    def test_datetime_object(self):
        result = Formatters.formatear_fecha(datetime(2026, 6, 29, 15, 30))
        assert result == "29/06/2026"

    def test_string_iso(self):
        result = Formatters.formatear_fecha("2026-06-29")
        assert result == "29/06/2026"

    def test_none(self):
        result = Formatters.formatear_fecha(None)
        assert result == ""


class TestTipoComprobante:
    def test_factura_a(self):
        assert "Factura A" in Formatters.tipo_comprobante_descripcion(1)

    def test_factura_c(self):
        assert "Factura C" in Formatters.tipo_comprobante_descripcion(11)

    def test_nota_credito(self):
        assert "Nota de Credito" in Formatters.tipo_comprobante_descripcion(3)
