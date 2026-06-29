import re
from datetime import datetime, date
from typing import Optional, Union
from babel.numbers import format_currency, format_decimal
from babel.dates import format_date, format_datetime


class Formatters:
    LOCALE = "es_AR"

    @staticmethod
    def formatear_importe(valor: Union[float, int, str], moneda: str = "ARS") -> str:
        try:
            valor_float = float(valor)
            return format_currency(valor_float, moneda, locale=Formatters.LOCALE)
        except (ValueError, TypeError):
            return "$ 0,00"

    @staticmethod
    def formatear_importe_sin_moneda(valor: Union[float, int, str]) -> str:
        try:
            valor_float = float(valor)
            return format_decimal(valor_float, locale=Formatters.LOCALE)
        except (ValueError, TypeError):
            return "0,00"

    @staticmethod
    def formatear_cuit(cuit: Union[str, int]) -> str:
        cuit_str = str(cuit).replace("-", "").replace(" ", "").replace("/", "")
        if len(cuit_str) == 11:
            return f"{cuit_str[:2]}-{cuit_str[2:10]}-{cuit_str[10:]}"
        return cuit_str

    @staticmethod
    def formatear_fecha(fecha: Optional[Union[datetime, date, str]], formato: str = "%d/%m/%Y") -> str:
        if fecha is None:
            return ""
        if isinstance(fecha, str):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%d-%m-%Y"):
                try:
                    fecha = datetime.strptime(fecha, fmt)
                    break
                except ValueError:
                    continue
            else:
                return fecha
            return fecha.strftime(formato)
        return fecha.strftime(formato)

    @staticmethod
    def formatear_fecha_hora(fecha: Optional[Union[datetime, str]], formato: str = "%d/%m/%Y %H:%M:%S") -> str:
        if fecha is None:
            return ""
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha)
            except ValueError:
                return fecha
        return fecha.strftime(formato)

    @staticmethod
    def formatear_cbu(cbu: str) -> str:
        cbu = cbu.replace("-", "").replace(" ", "")
        if len(cbu) == 22:
            return f"{cbu[:4]} {cbu[4:8]} {cbu[8:13]} {cbu[13:17]} {cbu[17:21]} {cbu[21:]}"
        return cbu

    @staticmethod
    def formatear_telefono(tel: str) -> str:
        tel = re.sub(r"[^\d+]", "", tel)
        if len(tel) == 10 and tel.startswith("11"):
            return f"({tel[:2]}) {tel[2:6]}-{tel[6:]}"
        if len(tel) == 11:
            return f"+{tel[:2]} ({tel[2:5]}) {tel[5:9]}-{tel[9:]}"
        if len(tel) == 8:
            return f"{tel[:4]}-{tel[4:]}"
        return tel

    @staticmethod
    def formatear_porcentaje(valor: float) -> str:
        return f"{valor:.2f}%".replace(".", ",")

    @staticmethod
    def formatear_numero(valor: Union[float, int], decimales: int = 2) -> str:
        try:
            valor_float = float(valor)
            return format_decimal(round(valor_float, decimales), locale=Formatters.LOCALE)
        except (ValueError, TypeError):
            return "0"

    @staticmethod
    def formatear_cae(cae: str) -> str:
        cae = cae.strip()
        if len(cae) == 14:
            return f"{cae[:2]}-{cae[2:8]}-{cae[8:]}"
        return cae

    @staticmethod
    def tipo_comprobante_descripcion(tipo: int) -> str:
        TIPOS = {
            1: "Factura A",
            2: "Nota de Debito A",
            3: "Nota de Credito A",
            6: "Factura B",
            7: "Nota de Debito B",
            8: "Nota de Credito B",
            11: "Factura C",
            12: "Nota de Debito C",
            13: "Nota de Credito C",
            19: "Factura E",
            20: "Nota de Debito E",
            21: "Nota de Credito E",
            51: "Factura M",
            52: "Nota de Debito M",
            53: "Nota de Credito M",
            81: "Factura",
            82: "Nota de Debito",
            83: "Nota de Credito",
        }
        return TIPOS.get(tipo, f"Tipo {tipo}")

    @staticmethod
    def estado_comprobante(estado: str) -> str:
        ESTADOS = {
            "EMITIDA": "Emitida",
            "ANULADA": "Anulada",
            "ERROR": "Error",
            "PENDIENTE": "Pendiente",
        }
        return ESTADOS.get(estado, estado)

    @staticmethod
    def condicion_iva_descripcion(codigo: int) -> str:
        CONDICIONES = {
            1: "IVA Responsable Inscripto",
            2: "IVA Responsable no Inscripto",
            3: "IVA Exento",
            4: "IVA Sujeto Exento",
            5: "Consumidor Final",
            6: "Responsable Monotributo",
            7: "Sujeto no Categorizado",
            8: "Proveedor del Exterior",
            9: "Cliente del Exterior",
            10: "IVA Liberado - Ley N° 19.640",
            11: "IVA Responsable Inscripto - Agente de Percepcion",
            12: "Pequeño Contribuyente Eventual",
            13: "Monotributista Social",
            14: "Pequeño Contribuyente Eventual Social",
        }
        return CONDICIONES.get(codigo, f"Codigo {codigo}")

    @staticmethod
    def alias_moneda(codigo: str) -> str:
        MONEDAS = {
            "ARS": "Pesos Argentinos",
            "USD": "Dolares Estadounidenses",
            "EUR": "Euros",
            "BRL": "Reales Brasileños",
            "CLP": "Pesos Chilenos",
            "UYU": "Pesos Uruguayos",
        }
        return MONEDAS.get(codigo, codigo)
