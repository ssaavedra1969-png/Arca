import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, grey, white
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, PageBreak, Frame, PageTemplate, BaseDocTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF
from loguru import logger

from config import ConfigManager
from utils.formatters import Formatters

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 20 * mm
MARGIN_RIGHT = 20 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 20 * mm


class FacturaPDF:
    def __init__(self, settings=None):
        self.settings = settings or ConfigManager.get_settings()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name="Titulo",
            fontName="Helvetica-Bold",
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ))
        self.styles.add(ParagraphStyle(
            name="Subtitulo",
            fontName="Helvetica-Bold",
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ))
        self.styles.add(ParagraphStyle(
            name="Dato",
            fontName="Helvetica",
            fontSize=8,
            alignment=TA_LEFT,
            spaceAfter=1 * mm,
        ))
        self.styles.add(ParagraphStyle(
            name="DatoBold",
            fontName="Helvetica-Bold",
            fontSize=8,
            alignment=TA_LEFT,
            spaceAfter=1 * mm,
        ))
        self.styles.add(ParagraphStyle(
            name="DatoDer",
            fontName="Helvetica",
            fontSize=8,
            alignment=TA_RIGHT,
            spaceAfter=1 * mm,
        ))
        self.styles.add(ParagraphStyle(
            name="Producto",
            fontName="Helvetica",
            fontSize=7,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="ProductoDer",
            fontName="Helvetica",
            fontSize=7,
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            name="Footer",
            fontName="Helvetica",
            fontSize=7,
            alignment=TA_CENTER,
            textColor=grey,
        ))

    def generar(self, factura_data: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
        )

        elements = []
        elements.extend(self._build_encabezado(factura_data))
        elements.append(Spacer(1, 3 * mm))
        elements.extend(self._build_datos_cliente(factura_data))
        elements.append(Spacer(1, 3 * mm))
        elements.extend(self._build_tabla_productos(factura_data.get("detalles", [])))
        elements.append(Spacer(1, 3 * mm))
        elements.extend(self._build_resumen(factura_data))
        elements.append(Spacer(1, 5 * mm))
        elements.extend(self._build_cae_qr(factura_data))
        elements.append(Spacer(1, 3 * mm))
        elements.extend(self._build_observaciones(factura_data))
        elements.append(Spacer(1, 5 * mm))
        elements.append(Paragraph(
            self.settings.report_footer or "Gracias por su compra",
            self.styles["Footer"],
        ))

        doc.build(elements)

        if output_path:
            with open(output_path, "wb") as f:
                f.write(buffer.getvalue())

        return buffer.getvalue()

    def _build_encabezado(self, data: Dict[str, Any]) -> List:
        elements = []

        logo_path = self.settings.report_logo
        if logo_path and Path(logo_path).exists():
            try:
                img = Image(logo_path, width=50 * mm, height=20 * mm)
                elements.append(img)
            except Exception:
                pass

        elements.append(Paragraph("FACTURA ELECTRONICA", self.styles["Titulo"]))

        tipo = Formatters.tipo_comprobante_descripcion(data.get("tipo_comprobante", 0))
        elements.append(Paragraph(tipo, self.styles["Subtitulo"]))

        pv = data.get("punto_venta", 0)
        numero = data.get("numero_factura", "")
        elements.append(Paragraph(
            f"Punto de Venta: {pv:04d} - Nº {numero:08d}",
            self.styles["Subtitulo"],
        ))

        return elements

    def _build_datos_cliente(self, data: Dict[str, Any]) -> List:
        cuit = Formatters.formatear_cuit(data.get("cuit_cliente", ""))
        cond_iva = Formatters.condicion_iva_descripcion(data.get("condicion_iva_cliente", 5))
        fecha = Formatters.formatear_fecha(data.get("fecha_emision"))

        datos = [
            [Paragraph("DATOS DEL EMISOR", self.styles["DatoBold"]),
             Paragraph("DATOS DEL CLIENTE", self.styles["DatoBold"])],
            [Paragraph(f"CUIT: {cuit}", self.styles["Dato"]),
             Paragraph(f"CUIT: {cuit}", self.styles["Dato"])],
            [Paragraph(f"Razon Social: {data.get('razon_social_cliente', '')}", self.styles["Dato"]),
             Paragraph(f"Razon Social: {data.get('razon_social_cliente', '')}", self.styles["Dato"])],
            [Paragraph(f"Condicion IVA: {cond_iva}", self.styles["Dato"]),
             Paragraph(f"Condicion IVA: {cond_iva}", self.styles["Dato"])],
            [Paragraph(f"Domicilio: {data.get('domicilio_cliente', '')}", self.styles["Dato"]),
             Paragraph(f"Domicilio: {data.get('domicilio_cliente', '')}", self.styles["Dato"])],
            [Paragraph(f"Fecha Emision: {fecha}", self.styles["Dato"]),
             Paragraph(f"Fecha Emision: {fecha}", self.styles["Dato"])],
        ]

        t = Table(datos, colWidths=[85 * mm, 85 * mm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, grey),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#E8E8E8")),
        ]))
        return [t]

    def _build_tabla_productos(self, detalles: List[Dict[str, Any]]) -> List:
        if not detalles:
            return [Paragraph("Sin detalles", self.styles["Dato"])]

        header = [
            Paragraph("Codigo", self.styles["DatoBold"]),
            Paragraph("Descripcion", self.styles["DatoBold"]),
            Paragraph("Cant.", self.styles["DatoBold"]),
            Paragraph("P.Unit.", self.styles["DatoBold"]),
            Paragraph("IVA%", self.styles["DatoBold"]),
            Paragraph("Subtotal", self.styles["DatoBold"]),
        ]

        data = [header]
        for det in detalles:
            data.append([
                Paragraph(str(det.get("codigo_producto", "") or ""), self.styles["Producto"]),
                Paragraph(det.get("descripcion", ""), self.styles["Producto"]),
                Paragraph(str(det.get("cantidad", 0)), self.styles["ProductoDer"]),
                Paragraph(Formatters.formatear_importe(det.get("precio_unitario", 0)), self.styles["ProductoDer"]),
                Paragraph(f"{det.get('alicuota_iva', 21):.0f}%", self.styles["ProductoDer"]),
                Paragraph(Formatters.formatear_importe(det.get("subtotal", 0)), self.styles["ProductoDer"]),
            ])

        col_widths = [20 * mm, 55 * mm, 15 * mm, 25 * mm, 12 * mm, 25 * mm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#E8E8E8")),
            ("GRID", (0, 0), (-1, -1), 0.5, grey),
            ("ALIGN", (2, 0), (5, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return [t]

    def _build_resumen(self, data: Dict[str, Any]) -> List:
        subtotal = data.get("subtotal", 0)
        iva = data.get("iva_total", 0)
        percepcion_iibb = data.get("percepcion_iibb", 0)
        percepcion_iva = data.get("percepcion_iva", 0)
        otros = data.get("otros_impuestos", 0)
        bonif = data.get("bonificacion", 0)
        total = data.get("total", 0)

        rows = [
            [Paragraph("Subtotal:", self.styles["Dato"]),
             Paragraph(Formatters.formatear_importe(subtotal), self.styles["DatoDer"])],
            [Paragraph("IVA:", self.styles["Dato"]),
             Paragraph(Formatters.formatear_importe(iva), self.styles["DatoDer"])],
        ]

        if percepcion_iibb:
            rows.append([
                Paragraph("Percepcion IIBB:", self.styles["Dato"]),
                Paragraph(Formatters.formatear_importe(percepcion_iibb), self.styles["DatoDer"]),
            ])
        if percepcion_iva:
            rows.append([
                Paragraph("Percepcion IVA:", self.styles["Dato"]),
                Paragraph(Formatters.formatear_importe(percepcion_iva), self.styles["DatoDer"]),
            ])
        if bonif:
            rows.append([
                Paragraph("Bonificacion:", self.styles["Dato"]),
                Paragraph(f"- {Formatters.formatear_importe(bonif)}", self.styles["DatoDer"]),
            ])

        rows.append([
            Paragraph("TOTAL:", self.styles["DatoBold"]),
            Paragraph(Formatters.formatear_importe(total), ParagraphStyle(
                "TotalDer", fontName="Helvetica-Bold", fontSize=12, alignment=TA_RIGHT,
            )),
        ])

        col_widths = [120 * mm, 50 * mm]
        t = Table(rows, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("LINEABOVE", (0, -1), (-1, -1), 1, black),
            ("LINEBELOW", (0, -1), (-1, -1), 1, black),
            ("TOPPADDING", (0, -1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 4),
        ]))
        return [t]

    def _build_cae_qr(self, data: Dict[str, Any]) -> List:
        cae = data.get("cae", "")
        cae_fmt = Formatters.formatear_cae(cae)
        cae_vto = data.get("cae_vencimiento", "")
        if isinstance(cae_vto, datetime):
            cae_vto = cae_vto.strftime("%d/%m/%Y")

        qr_data = (
            f"https://www.afip.gob.ar/fe/consultarFactura.asp?cae={cae}"
            if cae else ""
        )

        elements = []

        if qr_data:
            try:
                qr = QrCodeWidget(qr_data, barWidth=6 * mm, barHeight=6 * mm)
                d = Drawing(25 * mm, 25 * mm)
                d.add(qr)
                elements.append(d)
            except Exception:
                pass

        elements.append(Paragraph(
            f"CAE: {cae_fmt} - Vto: {cae_vto}",
            self.styles["DatoBold"],
        ))

        return elements

    def _build_observaciones(self, data: Dict[str, Any]) -> List:
        obs = data.get("observaciones", "")
        if obs:
            return [
                Paragraph("Observaciones:", self.styles["DatoBold"]),
                Paragraph(obs, self.styles["Dato"]),
            ]
        return []


def generate_factura_pdf(factura_data: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
    pdf = FacturaPDF()
    return pdf.generar(factura_data, output_path)
