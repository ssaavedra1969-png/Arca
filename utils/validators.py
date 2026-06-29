import re
from typing import Optional, Tuple


class ARCAValidators:
    CUIT_MULTIPLIERS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

    @staticmethod
    def validar_cuit(cuit: str) -> Tuple[bool, Optional[str]]:
        if not cuit:
            return False, "CUIT no puede estar vacio"

        cuit = cuit.replace("-", "").replace(" ", "").replace("/", "")

        if not cuit.isdigit():
            return False, "CUIT debe contener solo digitos"

        if len(cuit) != 11:
            return False, f"CUIT debe tener 11 digitos (tiene {len(cuit)})"

        tipo = int(cuit[:2])
        if tipo not in (20, 23, 24, 27, 30, 33, 34):
            return False, f"Tipo de CUIT invalido: {tipo}"

        if cuit == "00000000000" or cuit == "11111111111":
            return False, "CUIT invalido: todos digitos iguales"

        try:
            digito_calc = ARCAValidators._calcular_digito_verificador(cuit[:10])
            digito_real = int(cuit[10])
            if digito_calc != digito_real:
                return False, f"Digito verificador invalido (calculado: {digito_calc}, provisto: {digito_real})"
        except (ValueError, IndexError):
            return False, "Error al calcular digito verificador"

        cuit_formateado = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10:]}"
        return True, cuit_formateado

    @staticmethod
    def _calcular_digito_verificador(cuit_base: str) -> int:
        suma = 0
        for i, digito in enumerate(cuit_base):
            suma += int(digito) * ARCAValidators.CUIT_MULTIPLIERS[i]
        resto = suma % 11
        digito = 11 - resto
        if digito == 11:
            return 0
        if digito == 10:
            return 9
        return digito

    @staticmethod
    def validar_cbu(cbu: str) -> Tuple[bool, Optional[str]]:
        if not cbu:
            return False, "CBU no puede estar vacio"
        cbu = cbu.replace("-", "").replace(" ", "")
        if not cbu.isdigit():
            return False, "CBU debe contener solo digitos"
        if len(cbu) != 22:
            return False, f"CBU debe tener 22 digitos (tiene {len(cbu)})"

        banco = cbu[:8]
        cuenta = cbu[8:]
        if not ARCAValidators._validar_cbu_bloque(banco, 7):
            return False, "Digito verificador del banco invalido"
        if not ARCAValidators._validar_cbu_bloque(cuenta, 7):
            return False, "Digito verificador de la cuenta invalido"
        return True, cbu

    @staticmethod
    def _validar_cbu_bloque(bloque: str, largo: int) -> bool:
        pesos = [3, 1, 7, 9] if largo == 7 else [3, 1, 7, 9, 5, 1, 7, 9, 3, 1, 7, 9, 5, 1, 7, 9, 3, 1, 7]
        suma = 0
        for i, d in enumerate(bloque[:-1]):
            suma += int(d) * pesos[i % len(pesos)]
        resto = suma % 10
        dv = 10 - resto if resto != 0 else 0
        return dv == int(bloque[-1])

    @staticmethod
    def validar_email(email: str) -> Tuple[bool, Optional[str]]:
        if not email:
            return False, "Email no puede estar vacio"
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(patron, email):
            return False, "Formato de email invalido"
        if len(email) > 254:
            return False, "Email demasiado largo"
        return True, email.lower()

    @staticmethod
    def validar_importe(importe: str) -> Tuple[bool, Optional[float]]:
        if not importe:
            return False, "Importe no puede estar vacio"
        importe = importe.replace("$", "").replace(".", "").replace(",", ".").strip()
        try:
            valor = float(importe)
            if valor <= 0:
                return False, "El importe debe ser mayor a cero"
            if valor > 999999999999.99:
                return False, "El importe supera el maximo permitido"
            return True, round(valor, 2)
        except ValueError:
            return False, "Formato de importe invalido"

    @staticmethod
    def validar_telefono(telefono: str) -> Tuple[bool, Optional[str]]:
        if not telefono:
            return True, None
        telefono = telefono.replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
        if not telefono.isdigit():
            return False, "El telefono debe contener solo digitos, +, - y espacios"
        if len(telefono) < 6 or len(telefono) > 20:
            return False, "El telefono debe tener entre 6 y 20 digitos"
        return True, telefono

    @staticmethod
    def validar_codigo_postal(cp: str) -> bool:
        if not cp:
            return False
        cp = cp.strip().upper()
        if re.match(r'^[A-Z]\d{4}[A-Z]{3}$', cp):
            return True
        if re.match(r'^\d{4}$', cp):
            return True
        return False

    @staticmethod
    def validar_razon_social(rs: str) -> Tuple[bool, Optional[str]]:
        if not rs:
            return False, "Razon social no puede estar vacia"
        rs = rs.strip()
        if len(rs) < 3:
            return False, "Razon social debe tener al menos 3 caracteres"
        if len(rs) > 250:
            return False, "Razon social demasiado larga (max 250 caracteres)"
        if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\'.,&()/-]+$', rs):
            return False, "Razon social contiene caracteres no permitidos"
        return True, rs

    @staticmethod
    def sanitizar_input(texto: str) -> str:
        if not texto:
            return ""
        texto = texto.strip()
        texto = texto.replace("'", "''")
        texto = texto.replace(";", "")
        texto = texto.replace("--", "")
        texto = texto.replace("/*", "")
        texto = texto.replace("*/", "")
        return texto

    @staticmethod
    def formatear_cuit(cuit: str) -> str:
        cuit = cuit.replace("-", "").replace(" ", "").replace("/", "")
        if len(cuit) == 11:
            return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10:]}"
        return cuit
