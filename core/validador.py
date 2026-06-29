from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal
from loguru import logger

from config import ConfigManager
from utils.validators import ARCAValidators
from utils.formatters import Formatters
from utils.exceptions import ValidationError, BusinessError


class ValidadorARCA:
    ALICUOTAS_IVA = [0.0, 10.5, 21.0, 27.0, 5.0, 2.5]
    TIPOS_COMPROBANTE_FACTURA = [1, 6, 11, 19, 51]
    TIPOS_COMPROBANTE_ND = [2, 7, 12, 20, 52]
    TIPOS_COMPROBANTE_NC = [3, 8, 13, 21, 53]

    MONTOS_MAXIMOS_FACTURA_C = {
        "A": 128000.00,
        "B": 256000.00,
        "C": 512000.00,
        "D": 1024000.00,
        "E": 2048000.00,
        "F": 4096000.00,
        "G": 8192000.00,
        "H": 16384000.00,
        "I": 32768000.00,
        "J": 65536000.00,
        "K": 131072000.00,
    }

    def __init__(self, settings=None):
        self.settings = settings or ConfigManager.get_settings()

    def validar_factura(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errores = []

        tipo_cbte = data.get("tipo_comprobante", 0)
        if tipo_cbte not in range(1, 100):
            errores.append("Tipo de comprobante invalido")

        if not data.get("cuit_cliente"):
            errores.append("CUIT del cliente es requerido")
        else:
            valido, msg = ARCAValidators.validar_cuit(str(data["cuit_cliente"]))
            if not valido:
                errores.append(f"CUIT cliente invalido: {msg}")

        if not data.get("razon_social_cliente"):
            errores.append("Razon social del cliente es requerida")

        if not data.get("detalles") or len(data["detalles"]) == 0:
            errores.append("Debe ingresar al menos un detalle")
        else:
            for i, det in enumerate(data["detalles"]):
                errs = self._validar_detalle(det, i + 1)
                errores.extend(errs)

        total = data.get("total", 0)
        if total <= 0:
            errores.append("El total debe ser mayor a cero")

        if tipo_cbte in self.TIPOS_COMPROBANTE_NC:
            cae_orig = data.get("cae_original")
            if not cae_orig:
                errores.append("Nota de Credito requiere CAE del comprobante original")

        return len(errores) == 0, errores

    def _validar_detalle(self, det: Dict[str, Any], idx: int) -> List[str]:
        errores = []
        if not det.get("descripcion"):
            errores.append(f"Item {idx}: descripcion requerida")
        cantidad = det.get("cantidad", 0)
        if cantidad <= 0:
            errores.append(f"Item {idx}: cantidad debe ser mayor a cero")
        precio = det.get("precio_unitario", 0)
        if precio < 0:
            errores.append(f"Item {idx}: precio unitario no puede ser negativo")
        iva = det.get("alicuota_iva", 21)
        if iva not in self.ALICUOTAS_IVA:
            errores.append(f"Item {idx}: alicuota de IVA invalida ({iva})")
        return errores

    def validar_factura_c(self, total: float, condicion_iva_cliente: int,
                          categoria_monotributo: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        if condicion_iva_cliente not in (5, 6, 13):
            return False, "Factura C solo para Consumidor Final, Monotributista o Monotributista Social"

        if categoria_monotributo and categoria_monotributo.upper() in self.MONTOS_MAXIMOS_FACTURA_C:
            maximo = self.MONTOS_MAXIMOS_FACTURA_C[categoria_monotributo.upper()]
            if total > maximo:
                return False, f"El monto supera el maximo para categoria {categoria_monotributo} ($ {maximo:,.2f})"

        return True, None

    def validar_factura_a(self, condicion_iva_cliente: int) -> Tuple[bool, Optional[str]]:
        if condicion_iva_cliente not in (1, 4, 6, 8, 11, 12, 13):
            return False, "Factura A solo para Responsables Inscriptos"
        return True, None

    def validar_nota_credito(self, factura_original: Dict[str, Any],
                             nuevo_total: float) -> Tuple[bool, Optional[str]]:
        if not factura_original:
            return False, "Factura original no encontrada"
        if factura_original.get("estado") == "ANULADA":
            return False, "La factura original ya fue anulada"
        if nuevo_total > factura_original.get("total", 0):
            return False, "El monto de la Nota de Credito no puede superar el original"
        return True, None

    def validar_punto_venta(self, punto_venta: int) -> Tuple[bool, Optional[str]]:
        if punto_venta < 1 or punto_venta > 9999:
            return False, "Punto de venta debe estar entre 1 y 9999"
        if punto_venta not in self.settings.get("puntos_venta_habilitados", [punto_venta]):
            return False, f"Punto de venta {punto_venta} no habilitado"
        return True, None

    def validar_importes(self, subtotal: float, iva_total: float, total: float) -> Tuple[bool, Optional[str]]:
        if abs(subtotal + iva_total - total) > 0.01:
            return False, f"Discrepancia en totales: subtotal+iva ({subtotal + iva_total}) != total ({total})"
        return True, None

    def verificar_habilitacion_emisor(self, cuit: str, tipo_comprobante: int) -> bool:
        if self.settings.arca_homo:
            return True
        return True

    def validar_cuit_en_padron(self, cuit: str) -> Optional[Dict[str, Any]]:
        valido, msg = ARCAValidators.validar_cuit(cuit)
        if not valido:
            raise ValidationError(f"CUIT invalido: {msg}")

        try:
            from pyafipws.ws_sr_padron_a5 import WSSrPadronA5
            settings = ConfigManager.get_settings()

            ws = WSSrPadronA5()
            ws.Conectar()
            ws.Consultar(cuit)

            if ws.EsValido:
                return {
                    "cuit": cuit,
                    "razon_social": ws.RazonSocial,
                    "condicion_iva": ws.IdImpuesto,
                    "domicilio": ws.DomicilioFiscal,
                    "categoria": ws.CategoriaMonotributo if hasattr(ws, 'CategoriaMonotributo') else None,
                }
            return None
        except Exception as e:
            logger.warning(f"No se pudo consultar padron: {e}")
            return None

    def calcular_iva(self, importe: float, alicuota: float) -> float:
        if alicuota == 0:
            return 0.0
        return round(importe * alicuota / 100, 2)

    def calcular_percepcion_iibb(self, importe: float, porcentaje: float = 3.0) -> float:
        if porcentaje <= 0:
            return 0.0
        return round(importe * porcentaje / 100, 2)

    def calcular_percepcion_iva(self, importe: float, porcentaje: float = 5.0) -> float:
        if porcentaje <= 0:
            return 0.0
        return round(importe * porcentaje / 100, 2)
