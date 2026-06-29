import pytest
from utils.validators import ARCAValidators


class TestValidarCUIT:
    def test_cuit_valido_con_formato(self):
        valido, msg = ARCAValidators.validar_cuit("20-34567890-1")
        assert valido is True
        assert msg == "20-34567890-1"

    def test_cuit_valido_sin_formato(self):
        valido, msg = ARCAValidators.validar_cuit("20345678901")
        assert valido is True

    def test_cuit_digito_invalido(self):
        valido, msg = ARCAValidators.validar_cuit("20345678900")
        assert valido is False
        assert "Digito verificador" in msg

    def test_cuit_tipo_invalido(self):
        valido, msg = ARCAValidators.validar_cuit("10345678901")
        assert valido is False
        assert "Tipo de CUIT" in msg

    def test_cuit_longitud_invalida(self):
        valido, msg = ARCAValidators.validar_cuit("2034567890")
        assert valido is False

    def test_cuit_vacio(self):
        valido, msg = ARCAValidators.validar_cuit("")
        assert valido is False

    def test_cuit_todos_ceros(self):
        valido, msg = ARCAValidators.validar_cuit("00000000000")
        assert valido is False


class TestValidarCBU:
    def test_cbu_valido(self):
        valido, msg = ARCAValidators.validar_cbu("0000003100000000000022")
        assert valido is True

    def test_cbu_longitud_invalida(self):
        valido, msg = ARCAValidators.validar_cbu("00000")
        assert valido is False

    def test_cbu_vacio(self):
        valido, msg = ARCAValidators.validar_cbu("")
        assert valido is False


class TestValidarEmail:
    def test_email_valido(self):
        valido, msg = ARCAValidators.validar_email("test@example.com")
        assert valido is True

    def test_email_invalido(self):
        valido, msg = ARCAValidators.validar_email("test@")
        assert valido is False

    def test_email_vacio(self):
        valido, msg = ARCAValidators.validar_email("")
        assert valido is False


class TestValidarImporte:
    def test_importe_valido(self):
        valido, valor = ARCAValidators.validar_importe("1000.50")
        assert valido is True
        assert valor == 1000.50

    def test_importe_con_formato_argentino(self):
        valido, valor = ARCAValidators.validar_importe("$ 1.000,50")
        assert valido is True
        assert valor == 1000.50

    def test_importe_negativo(self):
        valido, msg = ARCAValidators.validar_importe("-100")
        assert valido is False


class TestSanitizarInput:
    def test_sql_injection(self):
        result = ARCAValidators.sanitizar_input("'; DROP TABLE usuarios; --")
        assert "'" not in result or result.count("'") == 2
        assert "DROP" in result

    def test_texto_normal(self):
        result = ARCAValidators.sanitizar_input("Cliente Normal S.A.")
        assert result == "Cliente Normal S.A."


class TestFormatearCUIT:
    def test_formateo(self):
        result = ARCAValidators.formatear_cuit("20345678901")
        assert result == "20-34567890-1"
