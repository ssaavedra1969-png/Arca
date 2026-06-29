from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pathlib import Path
from lxml import etree
from loguru import logger

from utils.formatters import Formatters


class XMLGenerator:
    NAMESPACES = {
        "fe": "http://ar.gov.afip.dif.FEV1/",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

    def generar_comprobante(self, factura_data: Dict[str, Any]) -> bytes:
        root = etree.Element("FacturaElectronica", nsmap=self.NAMESPACES)

        cabecera = etree.SubElement(root, "Cabecera")
        etree.SubElement(cabecera, "Cuit").text = str(factura_data.get("cuit_emisor", ""))
        etree.SubElement(cabecera, "PuntoVenta").text = str(factura_data.get("punto_venta", 0))
        etree.SubElement(cabecera, "TipoComprobante").text = str(factura_data.get("tipo_comprobante", 0))
        etree.SubElement(cabecera, "NumeroComprobante").text = str(factura_data.get("numero_factura", 0))
        etree.SubElement(cabecera, "FechaEmision").text = str(factura_data.get("fecha_emision", ""))
        etree.SubElement(cabecera, "CAE").text = str(factura_data.get("cae", ""))
        etree.SubElement(cabecera, "CAEVencimiento").text = str(factura_data.get("cae_vencimiento", ""))
        etree.SubElement(cabecera, "Resultado").text = str(factura_data.get("resultado", ""))
        etree.SubElement(cabecera, "Moneda").text = str(factura_data.get("moneda", "ARS"))
        etree.SubElement(cabecera, "Cotizacion").text = str(factura_data.get("cotizacion", 1))

        cliente = etree.SubElement(root, "Cliente")
        etree.SubElement(cliente, "CUIT").text = str(factura_data.get("cuit_cliente", ""))
        etree.SubElement(cliente, "RazonSocial").text = str(factura_data.get("razon_social_cliente", ""))
        etree.SubElement(cliente, "CondicionIVA").text = str(factura_data.get("condicion_iva_cliente", 5))
        etree.SubElement(cliente, "Domicilio").text = str(factura_data.get("domicilio_cliente", ""))

        detalles = etree.SubElement(root, "Detalles")
        for det in factura_data.get("detalles", []):
            item = etree.SubElement(detalles, "Item")
            etree.SubElement(item, "Descripcion").text = str(det.get("descripcion", ""))
            etree.SubElement(item, "Cantidad").text = str(det.get("cantidad", 0))
            etree.SubElement(item, "UnidadMedida").text = str(det.get("unidad_medida", "unidad"))
            etree.SubElement(item, "PrecioUnitario").text = str(det.get("precio_unitario", 0))
            etree.SubElement(item, "AlicuotaIVA").text = str(det.get("alicuota_iva", 21))
            etree.SubElement(item, "ImporteIVA").text = str(det.get("importe_iva", 0))
            etree.SubElement(item, "Bonificacion").text = str(det.get("bonificacion", 0))
            etree.SubElement(item, "Subtotal").text = str(det.get("subtotal", 0))

        totales = etree.SubElement(root, "Totales")
        etree.SubElement(totales, "Subtotal").text = str(factura_data.get("subtotal", 0))
        etree.SubElement(totales, "IVATotal").text = str(factura_data.get("iva_total", 0))
        etree.SubElement(totales, "PercepcionIIBB").text = str(factura_data.get("percepcion_iibb", 0))
        etree.SubElement(totales, "PercepcionIVA").text = str(factura_data.get("percepcion_iva", 0))
        etree.SubElement(totales, "OtrosImpuestos").text = str(factura_data.get("otros_impuestos", 0))
        etree.SubElement(totales, "Bonificacion").text = str(factura_data.get("bonificacion", 0))
        etree.SubElement(totales, "Total").text = str(factura_data.get("total", 0))

        if factura_data.get("observaciones"):
            etree.SubElement(root, "Observaciones").text = str(factura_data["observaciones"])

        xml_bytes = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        )
        return xml_bytes

    def generar_respuesta_arca(self, response_data: Dict[str, Any]) -> bytes:
        root = etree.Element("RespuestaARCA")

        etree.SubElement(root, "Resultado").text = str(response_data.get("resultado", ""))
        etree.SubElement(root, "CAE").text = str(response_data.get("cae", ""))
        etree.SubElement(root, "CAEVencimiento").text = str(response_data.get("cae_vencimiento", ""))

        if response_data.get("errores"):
            errores = etree.SubElement(root, "Errores")
            for err in response_data["errores"]:
                e = etree.SubElement(errores, "Error")
                etree.SubElement(e, "Codigo").text = str(err.get("codigo", ""))
                etree.SubElement(e, "Descripcion").text = str(err.get("descripcion", ""))

        if response_data.get("observaciones"):
            obs = etree.SubElement(root, "Observaciones")
            for ob in response_data["observaciones"]:
                o = etree.SubElement(obs, "Obs")
                etree.SubElement(o, "Codigo").text = str(ob.get("codigo", ""))
                etree.SubElement(o, "Descripcion").text = str(ob.get("descripcion", ""))

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")


def generar_xml_comprobante(factura_data: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
    gen = XMLGenerator()
    xml_bytes = gen.generar_comprobante(factura_data)
    if output_path:
        with open(output_path, "wb") as f:
            f.write(xml_bytes)
    return xml_bytes
