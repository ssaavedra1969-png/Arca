from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from threading import Thread
from pathlib import Path
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk

from config import ConfigManager
from database.repositories import FacturaRepository, ContribuyenteRepository
from database.models import get_session_factory
from utils.formatters import Formatters
from reports.excel_generator import ExcelGenerator
from loguru import logger
from ui.style import *


class PanelReportes(ctk.CTkFrame):
    def __init__(self, parent, settings, session_factory=None):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings
        self.session_factory = session_factory
        self.estadisticas: Dict[str, Any] = {}
        self.clientes_frecuentes: List = []
        self.pendientes_count = 0

        self._build_ui()

    def _card(self, parent, title=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=12,
                              border_width=1, border_color=COLOR_CARD_BORDER)
        if title:
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=16, pady=(12, 0))
            ctk.CTkLabel(header, text=title, font=FONT_SUBSECTION,
                          text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
            divider = ctk.CTkFrame(frame, fg_color=COLOR_WHITE_10, height=1)
            divider.pack(fill="x", padx=16, pady=(8, 0))
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)
        return frame, body

    def _btn(self, parent, text, command=None, **kwargs):
        kwargs.setdefault("fg_color", COLOR_BUTTON_PRIMARY)
        kwargs.setdefault("hover_color", COLOR_BUTTON_HOVER)
        kwargs.setdefault("text_color", "white")
        kwargs.setdefault("font", FONT_BODY)
        kwargs.setdefault("corner_radius", 8)
        return ctk.CTkButton(parent, text=text, command=command, **kwargs)

    def _build_ui(self):
        ctk.CTkLabel(self, text="Reportes y Estadísticas",
                      font=FONT_HEADING,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=4, pady=(0, 16))

        self._build_filtros()
        self._build_kpi_cards()
        self._build_tablas()
        self._build_acciones()

    def _build_filtros(self):
        card, body = self._card(self, "Período")
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(body, text="Periodo:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).pack(side="left", padx=(0, 8))

        self.periodo_combo = ctk.CTkOptionMenu(
            body,
            values=["Últimos 7 días", "Últimos 30 días", "Este mes",
                    "Este trimestre", "Este año", "Personalizado"],
            fg_color=COLOR_INPUT_BG, button_color=COLOR_GRADIENT_A,
            button_hover_color=COLOR_BUTTON_HOVER, text_color=COLOR_INPUT_TEXT,
            command=self._on_periodo_change, width=150,
        )
        self.periodo_combo.pack(side="left", padx=4)
        self.periodo_combo.set("Últimos 30 días")

        ctk.CTkLabel(body, text="Desde:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).pack(side="left", padx=(12, 4))
        self.desde_entry = ctk.CTkEntry(body, width=100,
                                         fg_color=COLOR_INPUT_BG,
                                         border_color=COLOR_INPUT_BORDER,
                                         text_color=COLOR_INPUT_TEXT)
        self.desde_entry.pack(side="left", padx=2)
        self.desde_entry.insert(0, (date.today() - timedelta(days=30)).strftime("%d/%m/%Y"))

        ctk.CTkLabel(body, text="Hasta:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).pack(side="left", padx=4)
        self.hasta_entry = ctk.CTkEntry(body, width=100,
                                         fg_color=COLOR_INPUT_BG,
                                         border_color=COLOR_INPUT_BORDER,
                                         text_color=COLOR_INPUT_TEXT)
        self.hasta_entry.pack(side="left", padx=2)
        self.hasta_entry.insert(0, date.today().strftime("%d/%m/%Y"))

        self._btn(body, "Actualizar", command=self.cargar_datos,
                   width=100).pack(side="left", padx=12)

    def _build_kpi_cards(self):
        card, body = self._card(self, "Indicadores Clave")
        card.pack(fill="x", pady=(0, 12))
        body.grid_columnconfigure((0, 1, 2, 3), weight=1)

        kpi_configs = [
            ("Facturas Emitidas", "0", COLOR_GRADIENT_A),
            ("Total Facturado", "$ 0,00", COLOR_GRADIENT_B),
            ("Pendientes", "0", COLOR_ORANGE),
            ("Certificado", "--", COLOR_RED),
        ]

        for col, (title, default, accent) in enumerate(kpi_configs):
            kpi_card = ctk.CTkFrame(body, fg_color="transparent", corner_radius=10,
                                     border_width=1, border_color=COLOR_CARD_BORDER)
            kpi_card.grid(row=0, column=col, padx=4, sticky="nsew")
            kpi_card.grid_propagate(False)
            kpi_card.configure(height=90)

            accent_bar = ctk.CTkFrame(kpi_card, fg_color=accent, height=3,
                                       corner_radius=0)
            accent_bar.pack(fill="x")

            ctk.CTkLabel(kpi_card, text=title, font=FONT_SMALL,
                          text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 0))

            if col == 0:
                self.kpi_facturas_valor = ctk.CTkLabel(
                    kpi_card, text=default, font=(FONT_FAMILY, 22, "bold"),
                    text_color=COLOR_TEXT_PRIMARY
                )
                self.kpi_facturas_valor.pack(anchor="w", padx=14, pady=(2, 10))
            elif col == 1:
                self.kpi_total_valor = ctk.CTkLabel(
                    kpi_card, text=default, font=(FONT_FAMILY, 22, "bold"),
                    text_color=COLOR_TEXT_PRIMARY
                )
                self.kpi_total_valor.pack(anchor="w", padx=14, pady=(2, 10))
            elif col == 2:
                self.kpi_pendientes_valor = ctk.CTkLabel(
                    kpi_card, text=default, font=(FONT_FAMILY, 22, "bold"),
                    text_color=COLOR_TEXT_PRIMARY
                )
                self.kpi_pendientes_valor.pack(anchor="w", padx=14, pady=(2, 10))
            elif col == 3:
                self.kpi_certificado_valor = ctk.CTkLabel(
                    kpi_card, text=default, font=(FONT_FAMILY, 22, "bold"),
                    text_color=COLOR_TEXT_PRIMARY
                )
                self.kpi_certificado_valor.pack(anchor="w", padx=14, pady=(2, 10))

    def _build_tablas(self):
        card, body = self._card(self)
        card.pack(fill="both", expand=True, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(body, text="Por Tipo de Comprobante",
                      font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).grid(
            row=0, column=0, pady=(0, 4)
        )
        ctk.CTkLabel(body, text="Clientes más Frecuentes",
                      font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).grid(
            row=0, column=1, pady=(0, 4)
        )

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#0D0D1F", foreground="#FFFFFF",
                        fieldbackground="#0D0D1F", borderwidth=0,
                        font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background="#1A1A3E", foreground="#FFFFFF",
                        borderwidth=0, font=(FONT_FAMILY, 10, "bold"))
        style.map("Treeview", background=[("selected", "#6C3CE1")])

        columns_tipo = ("Tipo", "Cantidad", "Total")
        self.tree_tipo = ttk.Treeview(body, columns=columns_tipo, show="headings", height=6)
        for col in columns_tipo:
            self.tree_tipo.heading(col, text=col)
        self.tree_tipo.grid(row=1, column=0, padx=4, sticky="nsew")

        columns_cli = ("CUIT", "Razón Social", "Facturas", "Total")
        self.tree_clientes = ttk.Treeview(body, columns=columns_cli, show="headings", height=6)
        for col in columns_cli:
            self.tree_clientes.heading(col, text=col)
        self.tree_clientes.grid(row=1, column=1, padx=4, sticky="nsew")

    def _build_acciones(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 8))

        self._btn(frame, "Exportar Reporte Excel",
                   command=self._exportar_reporte).pack(side="left", padx=4)
        self._btn(frame, "Actualizar Datos",
                   command=self.cargar_datos).pack(side="left", padx=4)

        self.status_label = ctk.CTkLabel(frame, text="", font=FONT_SMALL,
                                          text_color=COLOR_TEXT_MUTED)
        self.status_label.pack(side="right", padx=16)

    def cargar_datos(self):
        def task():
            try:
                desde = self._parse_fecha(self.desde_entry.get()) or (date.today() - timedelta(days=30))
                hasta = self._parse_fecha(self.hasta_entry.get()) or date.today()

                session = self.session_factory()
                try:
                    factura_repo = FacturaRepository(session)
                    stats = factura_repo.get_estadisticas(desde, hasta)

                    cliente_repo = ContribuyenteRepository(session)
                    clientes = cliente_repo.get_frecuentes(10)

                    pendientes = len(factura_repo.get_pendientes())

                    self.estadisticas = stats
                    self.clientes_frecuentes = clientes
                    self.pendientes_count = pendientes

                    self.after(0, self._actualizar_ui)
                finally:
                    session.close()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        Thread(target=task, daemon=True).start()

    def _actualizar_ui(self):
        stats = self.estadisticas

        self.kpi_facturas_valor.configure(text=str(stats.get("cantidad_facturas", 0)))
        self.kpi_total_valor.configure(
            text=Formatters.formatear_importe(stats.get("total_facturado", 0))
        )
        self.kpi_pendientes_valor.configure(text=str(self.pendientes_count))

        try:
            from core.auth import Authenticator
            auth = Authenticator(self.settings)
            info = auth.get_cert_info()
            dias = info.get("days_remaining", 0)
            if dias > 30:
                color = COLOR_TEXT_PRIMARY
            elif dias > 7:
                color = COLOR_ORANGE
            else:
                color = COLOR_RED
            self.kpi_certificado_valor.configure(
                text=f"{dias} días",
                text_color=color,
            )
        except Exception:
            self.kpi_certificado_valor.configure(text="N/A")

        self._llenar_tablas()

    def _llenar_tablas(self):
        for item in self.tree_tipo.get_children():
            self.tree_tipo.delete(item)
        for tipo, cant, total in self.estadisticas.get("por_tipo", []):
            self.tree_tipo.insert("", "end", values=(
                Formatters.tipo_comprobante_descripcion(tipo),
                cant,
                Formatters.formatear_importe(total),
            ))

        for item in self.tree_clientes.get_children():
            self.tree_clientes.delete(item)
        for cliente, cant in self.clientes_frecuentes:
            self.tree_clientes.insert("", "end", values=(
                Formatters.formatear_cuit(cliente.cuit),
                cliente.razon_social[:30],
                cant,
                "",
            ))

    def _on_periodo_change(self, choice):
        hoy = date.today()
        periodos = {
            "Últimos 7 días": (hoy - timedelta(days=7), hoy),
            "Últimos 30 días": (hoy - timedelta(days=30), hoy),
            "Este mes": (hoy.replace(day=1), hoy),
            "Este trimestre": (hoy.replace(month=((hoy.month - 1) // 3) * 3 + 1, day=1), hoy),
            "Este año": (hoy.replace(month=1, day=1), hoy),
        }
        if choice in periodos:
            desde, hasta = periodos[choice]
            self.desde_entry.delete(0, "end")
            self.desde_entry.insert(0, desde.strftime("%d/%m/%Y"))
            self.hasta_entry.delete(0, "end")
            self.hasta_entry.insert(0, hasta.strftime("%d/%m/%Y"))
            self.cargar_datos()

    def _exportar_reporte(self):
        filename = f"Reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=filename,
        )
        if filepath:
            def task():
                try:
                    gen = ExcelGenerator()
                    data = []
                    for mes, cant, total in self.estadisticas.get("por_mes", []):
                        data.append([mes, cant, "", "", total])
                    gen.generar_reporte_mensual(data, filepath)
                    self.after(0, lambda: messagebox.showinfo("Reporte", f"Reporte generado:\n{filepath}"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", str(e)))
            Thread(target=task, daemon=True).start()

    @staticmethod
    def _parse_fecha(texto: str) -> Optional[date]:
        if not texto:
            return None
        try:
            return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
        except ValueError:
            return None

    def on_activate(self):
        self.cargar_datos()
