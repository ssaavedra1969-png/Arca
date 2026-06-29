from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from threading import Thread
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk

from config import ConfigManager
from database.repositories import FacturaRepository
from database.models import get_session_factory
from utils.formatters import Formatters
from utils.validators import ARCAValidators
from reports.pdf_generator import generate_factura_pdf
from reports.excel_generator import exportar_historial_excel
from reports.xml_generator import generar_xml_comprobante
from loguru import logger
from ui.style import *


class PanelHistorial(ctk.CTkFrame):
    def __init__(self, parent, settings, session_factory=None):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings
        self.session_factory = session_factory
        self.facturas: List[Dict[str, Any]] = []
        self._filtros: Dict[str, Any] = {}

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
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Historial de Facturas",
                      font=FONT_HEADING,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=4, pady=(0, 16))

        self._build_filtros()
        self._build_tabla()
        self._build_acciones()

    def _build_filtros(self):
        card, body = self._card(self, "Filtros de Búsqueda")
        card.pack(fill="x", pady=(0, 12))
        body.grid_columnconfigure((1, 3, 5, 7, 9), weight=1)

        ctk.CTkLabel(body, text="Desde:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=0, padx=(0, 4), pady=3, sticky="w")
        self.fecha_desde = ctk.CTkEntry(body, placeholder_text="dd/mm/aaaa", width=100,
                                         fg_color=COLOR_INPUT_BG,
                                         border_color=COLOR_INPUT_BORDER,
                                         text_color=COLOR_INPUT_TEXT)
        self.fecha_desde.grid(row=0, column=1, padx=(0, 8), pady=3, sticky="ew")
        self.fecha_desde.insert(0, (date.today() - timedelta(days=30)).strftime("%d/%m/%Y"))

        ctk.CTkLabel(body, text="Hasta:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=2, padx=(0, 4), pady=3, sticky="w")
        self.fecha_hasta = ctk.CTkEntry(body, placeholder_text="dd/mm/aaaa", width=100,
                                         fg_color=COLOR_INPUT_BG,
                                         border_color=COLOR_INPUT_BORDER,
                                         text_color=COLOR_INPUT_TEXT)
        self.fecha_hasta.grid(row=0, column=3, padx=(0, 8), pady=3, sticky="ew")
        self.fecha_hasta.insert(0, date.today().strftime("%d/%m/%Y"))

        ctk.CTkLabel(body, text="Tipo:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=4, padx=(0, 4), pady=3, sticky="w")
        self.tipo_combo = ctk.CTkOptionMenu(
            body, values=["Todos", "Factura A", "Factura B", "Factura C",
                          "Nota Debito A", "Nota Credito A"],
            fg_color=COLOR_INPUT_BG, button_color=COLOR_GRADIENT_A,
            button_hover_color=COLOR_BUTTON_HOVER, text_color=COLOR_INPUT_TEXT,
            width=120,
        )
        self.tipo_combo.grid(row=0, column=5, padx=(0, 8), pady=3, sticky="ew")
        self.tipo_combo.set("Todos")

        ctk.CTkLabel(body, text="Estado:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=6, padx=(0, 4), pady=3, sticky="w")
        self.estado_combo = ctk.CTkOptionMenu(
            body, values=["Todos", "Emitida", "Pendiente", "Anulada", "Error", "Borrador"],
            fg_color=COLOR_INPUT_BG, button_color=COLOR_GRADIENT_A,
            button_hover_color=COLOR_BUTTON_HOVER, text_color=COLOR_INPUT_TEXT,
            width=100,
        )
        self.estado_combo.grid(row=0, column=7, padx=(0, 8), pady=3, sticky="ew")
        self.estado_combo.set("Todos")

        ctk.CTkLabel(body, text="Buscar:", font=FONT_BODY,
                      text_color=COLOR_TEXT_SECONDARY).grid(row=1, column=0, padx=(0, 4), pady=3, sticky="w")
        self.buscar_entry = ctk.CTkEntry(body, placeholder_text="CUIT o Razón Social",
                                          fg_color=COLOR_INPUT_BG,
                                          border_color=COLOR_INPUT_BORDER,
                                          text_color=COLOR_INPUT_TEXT)
        self.buscar_entry.grid(row=1, column=1, columnspan=6, padx=(0, 8), pady=3, sticky="ew")
        self.buscar_entry.bind("<Return>", lambda e: self.cargar_datos())

        self._btn(body, "Buscar", command=self.cargar_datos,
                   width=80).grid(row=1, column=7, padx=0, pady=3)

    def _build_tabla(self):
        card, body = self._card(self)
        card.pack(fill="both", expand=True, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#0D0D1F", foreground="#FFFFFF",
                        fieldbackground="#0D0D1F", borderwidth=0,
                        font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background="#1A1A3E", foreground="#FFFFFF",
                        borderwidth=0, font=(FONT_FAMILY, 10, "bold"))
        style.map("Treeview", background=[("selected", "#6C3CE1")])

        columns = ("Fecha", "Tipo", "PV", "Número", "Cliente", "CUIT", "Total",
                   "CAE", "Estado")
        self.tree = ttk.Treeview(body, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            widths = {
                "Fecha": 100, "Tipo": 130, "PV": 40, "Número": 70,
                "Cliente": 200, "CUIT": 110, "Total": 100,
                "CAE": 140, "Estado": 80,
            }
            self.tree.column(col, width=widths.get(col, 100), anchor="center")
            if col in ("Total",):
                self.tree.column(col, anchor="e")

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._on_doble_click)

        scroll_y = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll_y.set)

    def _build_acciones(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 8))

        self._btn(frame, "Ver Detalle", command=self._ver_detalle).pack(side="left", padx=4)
        self._btn(frame, "Exportar PDF", command=self._exportar_pdf).pack(side="left", padx=4)
        self._btn(frame, "Exportar Excel", command=self._exportar_excel).pack(side="left", padx=4)
        self._btn(frame, "XML Respaldo", command=self._exportar_xml).pack(side="left", padx=4)
        self._btn(frame, "Reemitir", command=self._reemitir).pack(side="left", padx=4)

        ctk.CTkButton(frame, text="Anular",
                       fg_color=COLOR_BUTTON_DANGER,
                       hover_color=COLOR_BUTTON_DANGER_HOVER,
                       text_color="white", font=FONT_BODY, corner_radius=8,
                       command=self._anular).pack(side="right", padx=4)

        self.status_label = ctk.CTkLabel(frame, text="", font=FONT_SMALL,
                                          text_color=COLOR_TEXT_MUTED)
        self.status_label.pack(side="right", padx=16)

    def cargar_datos(self):
        self._filtros = self._recoger_filtros()

        def task():
            session = self.session_factory()
            try:
                repo = FacturaRepository(session)
                resultados, total = repo.search(self._filtros, limit=500)
                self.facturas = [
                    {
                        "id": f.id,
                        "fecha_emision": f.fecha_emision,
                        "tipo_comprobante": f.tipo_comprobante,
                        "punto_venta": f.punto_venta,
                        "numero_factura": f.numero_factura,
                        "razon_social_cliente": f.razon_social_cliente,
                        "cuit_cliente": f.cuit_cliente,
                        "total": f.total,
                        "cae": f.cae,
                        "estado": f.estado,
                        "uuid": f.uuid,
                        "detalles": [
                            {
                                "descripcion": d.descripcion,
                                "cantidad": d.cantidad,
                                "precio_unitario": d.precio_unitario,
                                "alicuota_iva": d.alicuota_iva,
                                "subtotal": d.subtotal,
                            }
                            for d in f.detalles
                        ],
                        "subtotal": f.subtotal,
                        "iva_total": f.iva_total,
                        "observaciones": f.observaciones,
                        "domicilio_cliente": f.domicilio_cliente,
                        "condicion_iva_cliente": f.condicion_iva_cliente,
                        "moneda": f.moneda,
                        "cae_vencimiento": f.cae_vencimiento,
                    }
                    for f in resultados
                ]
                self.after(0, self._llenar_tabla)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                session.close()

        Thread(target=task, daemon=True).start()

    def _recoger_filtros(self) -> Dict[str, Any]:
        filtros = {}

        desde = self.fecha_desde.get().strip()
        if desde:
            try:
                filtros["fecha_desde"] = datetime.strptime(desde, "%d/%m/%Y")
            except ValueError:
                pass

        hasta = self.fecha_hasta.get().strip()
        if hasta:
            try:
                filtros["fecha_hasta"] = datetime.strptime(hasta, "%d/%m/%Y")
            except ValueError:
                pass

        tipo = self.tipo_combo.get()
        TIPO_MAP = {"Factura A": 1, "Factura B": 6, "Factura C": 11,
                    "Nota Debito A": 2, "Nota Credito A": 3}
        if tipo in TIPO_MAP:
            filtros["tipo_comprobante"] = TIPO_MAP[tipo]

        estado = self.estado_combo.get()
        ESTADO_MAP = {"Emitida": "EMITIDA", "Pendiente": "PENDIENTE",
                      "Anulada": "ANULADA", "Error": "ERROR", "Borrador": "BORRADOR"}
        if estado in ESTADO_MAP:
            filtros["estado"] = ESTADO_MAP[estado]

        busqueda = self.buscar_entry.get().strip()
        if busqueda:
            if busqueda.replace("-", "").isdigit() and len(busqueda.replace("-", "")) >= 7:
                filtros["cuit_cliente"] = busqueda
            else:
                filtros["razon_social"] = busqueda

        return filtros

    def _llenar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for fac in self.facturas:
            self.tree.insert("", "end", values=(
                Formatters.formatear_fecha(fac["fecha_emision"]),
                Formatters.tipo_comprobante_descripcion(fac["tipo_comprobante"]),
                f"{fac['punto_venta']:04d}",
                fac["numero_factura"] or "",
                fac["razon_social_cliente"][:40],
                Formatters.formatear_cuit(fac["cuit_cliente"]),
                Formatters.formatear_importe(fac["total"]),
                Formatters.formatear_cae(fac.get("cae") or ""),
                Formatters.estado_comprobante(fac["estado"]),
            ))

        self.status_label.configure(
            text=f"Mostrando {len(self.facturas)} facturas"
        )

    def _on_doble_click(self, event):
        self._ver_detalle()

    def _ver_detalle(self):
        factura = self._get_seleccionada()
        if not factura:
            return

        top = ctk.CTkToplevel(self)
        top.title(f"Detalle Factura #{factura['numero_factura']}")
        top.geometry("650x600")
        top.transient(self)
        top.grab_set()
        top.configure(fg_color=COLOR_BG)

        main = ctk.CTkFrame(top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text=f"Factura #{factura['numero_factura']}",
                      font=FONT_SECTION,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")

        divider = ctk.CTkFrame(main, fg_color=COLOR_WHITE_10, height=1)
        divider.pack(fill="x", pady=(8, 12))

        det_frame = ctk.CTkFrame(main, fg_color="transparent")
        det_frame.pack(fill="both", expand=True)
        det_frame.grid_columnconfigure(1, weight=1)

        items = [
            ("UUID:", factura.get('uuid', 'N/A')),
            ("Tipo:", Formatters.tipo_comprobante_descripcion(factura['tipo_comprobante'])),
            ("Pto. Venta:", f"{factura['punto_venta']:04d}"),
            ("Número:", str(factura['numero_factura'] or 'N/A')),
            ("Fecha:", Formatters.formatear_fecha(factura['fecha_emision'])),
            ("Cliente:", factura['razon_social_cliente']),
            ("CUIT:", Formatters.formatear_cuit(factura['cuit_cliente'])),
            ("Domicilio:", factura.get('domicilio_cliente', 'N/A')),
            ("Cond. IVA:", Formatters.condicion_iva_descripcion(factura.get('condicion_iva_cliente', 5))),
            ("Moneda:", factura.get('moneda', 'ARS')),
            ("", ""),
            ("Subtotal:", Formatters.formatear_importe(factura.get('subtotal', 0))),
            ("IVA:", Formatters.formatear_importe(factura.get('iva_total', 0))),
            ("TOTAL:", Formatters.formatear_importe(factura['total'])),
            ("", ""),
            ("CAE:", Formatters.formatear_cae(factura.get('cae') or '')),
            ("Vto CAE:", Formatters.formatear_fecha(factura.get('cae_vencimiento'))),
            ("Estado:", Formatters.estado_comprobante(factura['estado'])),
        ]

        for i, (label, value) in enumerate(items):
            if label:
                ctk.CTkLabel(det_frame, text=label, font=FONT_BODY,
                              text_color=COLOR_TEXT_SECONDARY).grid(
                    row=i, column=0, sticky="w", pady=1, padx=(0, 8))
                ctk.CTkLabel(det_frame, text=value, font=FONT_BODY,
                              text_color=COLOR_TEXT_PRIMARY).grid(
                    row=i, column=1, sticky="w", pady=1)
            else:
                divider2 = ctk.CTkFrame(det_frame, fg_color=COLOR_WHITE_10, height=1)
                divider2.grid(row=i, column=0, columnspan=2, sticky="ew", pady=4)

        if factura.get("observaciones"):
            ctk.CTkLabel(main, text=f"Observaciones: {factura['observaciones']}",
                          font=FONT_BODY, text_color=COLOR_TEXT_SECONDARY,
                          wraplength=500, justify="left").pack(anchor="w", pady=(8, 0))

        if factura.get("detalles"):
            ctk.CTkLabel(main, text="Detalles:", font=FONT_BODY,
                          text_color=COLOR_TEXT_SECONDARY).pack(anchor="w", pady=(12, 4))
            for det in factura["detalles"]:
                ctk.CTkLabel(main,
                              text=f"  {det['descripcion'][:50]} x{det['cantidad']} @ {Formatters.formatear_importe(det['precio_unitario'])} = {Formatters.formatear_importe(det['subtotal'])}",
                              font=(FONT_FAMILY, 10), text_color=COLOR_TEXT_MUTED,
                              wraplength=580, justify="left").pack(anchor="w")

        ctk.CTkButton(main, text="Cerrar", command=top.destroy,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER,
                       corner_radius=8).pack(pady=(16, 0))

    def _exportar_pdf(self):
        factura = self._get_seleccionada()
        if not factura:
            return

        filename = f"Factura_{factura['tipo_comprobante']}_{factura['punto_venta']:04d}-{factura.get('numero_factura', 0):08d}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=filename,
        )
        if filepath:
            def task():
                try:
                    generate_factura_pdf(factura, filepath)
                    self.after(0, lambda: (
                        messagebox.showinfo("PDF", f"PDF generado:\n{filepath}"),
                        Path(filepath).exists() and __import__('os').startfile(filepath),
                    ))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", str(e)))
            Thread(target=task, daemon=True).start()

    def _exportar_excel(self):
        if not self.facturas:
            messagebox.showinfo("Exportar", "No hay datos para exportar")
            return

        filename = f"Historial_Facturas_{datetime.now().strftime('%Y%m%d')}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=filename,
        )
        if filepath:
            def task():
                try:
                    exportar_historial_excel(self.facturas, filepath)
                    self.after(0, lambda: (
                        messagebox.showinfo("Excel", f"Excel generado:\n{filepath}"),
                    ))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", str(e)))
            Thread(target=task, daemon=True).start()

    def _exportar_xml(self):
        factura = self._get_seleccionada()
        if not factura:
            return

        filename = f"Factura_{factura['tipo_comprobante']}_{factura['punto_venta']:04d}-{factura.get('numero_factura', 0):08d}.xml"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")],
            initialfile=filename,
        )
        if filepath:
            def task():
                try:
                    generar_xml_comprobante(factura, filepath)
                    self.after(0, lambda: messagebox.showinfo("XML", f"XML generado:\n{filepath}"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", str(e)))
            Thread(target=task, daemon=True).start()

    def _reemitir(self):
        factura = self._get_seleccionada()
        if not factura:
            return

        if not messagebox.askyesno("Reemitir", f"Reemitir factura #{factura['numero_factura']}?"):
            return

        session = self.session_factory()
        try:
            repo = FacturaRepository(session)
            original = repo.get_by_id(factura["id"])
            if not original:
                messagebox.showerror("Error", "Factura original no encontrada")
                return

            nueva = repo.reemitir(original.id)
            session.commit()

            messagebox.showinfo(
                "Reemision",
                f"Factura reemitida como borrador (ID: {nueva.id})\n"
                f"Complete los datos y genere la factura desde el panel de Facturacion"
            )
            self.cargar_datos()
        except Exception as e:
            session.rollback()
            messagebox.showerror("Error", f"Error reemitiendo: {e}")
        finally:
            session.close()

    def _anular(self):
        factura = self._get_seleccionada()
        if not factura:
            return

        if factura["estado"] == "ANULADA":
            messagebox.showinfo("Anular", "Esta factura ya fue anulada")
            return

        if not messagebox.askyesno("Anular", f"Esta seguro de anular la factura #{factura['numero_factura']}?\n\nEsta accion no se puede deshacer."):
            return

        dialog = ctk.CTkInputDialog(
            text="Motivo de anulacion:",
            title="Anular Factura",
        )
        motivo = dialog.get_input()
        if not motivo:
            return

        from core.facturador import Facturador
        facturador = Facturador(self.settings)
        facturador.initialize(self.session_factory)

        ok, msg = facturador.anular_comprobante(factura["id"], motivo)
        if ok:
            messagebox.showinfo("Anulada", "Factura anulada correctamente")
            self.cargar_datos()
        else:
            messagebox.showerror("Error", msg)

    def _get_seleccionada(self) -> Optional[Dict[str, Any]]:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleccion", "Seleccione una factura de la lista")
            return None
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.facturas):
            return self.facturas[idx]
        return None

    def on_activate(self):
        self.cargar_datos()
