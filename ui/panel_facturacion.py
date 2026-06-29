import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import customtkinter as ctk

from config import ConfigManager
from core.facturador import Facturador
from core.models import FacturaModel, DetalleFacturaModel
from database.repositories import (
    ContribuyenteRepository, ProductoRepository, FacturaRepository
)
from database.models import get_session_factory, TipoComprobante
from utils.formatters import Formatters
from utils.validators import ARCAValidators
from utils.exceptions import ValidationError
from reports.pdf_generator import generate_factura_pdf
from loguru import logger
from ui.style import *


class PanelFacturacion(ctk.CTkFrame):
    TIPOS_COMPROBANTE = {
        "Factura A (RI)": 1,
        "Nota Debito A": 2,
        "Nota Credito A": 3,
        "Factura B (CF)": 6,
        "Nota Debito B": 7,
        "Nota Credito B": 8,
        "Factura C (Monotributo)": 11,
        "Nota Debito C": 12,
        "Nota Credito C": 13,
    }

    def __init__(self, parent, settings, facturador: Optional[Facturador],
                 session_factory=None):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings
        self.facturador = facturador
        self.session_factory = session_factory
        self.detalles: List[Dict[str, Any]] = []
        self.editando_idx: Optional[int] = None

        self._build_ui()

    def _card(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=12,
                              border_width=1, border_color=COLOR_CARD_BORDER)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(header, text=title, font=FONT_SUBSECTION,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        divider = ctk.CTkFrame(frame, fg_color=COLOR_WHITE_10, height=1)
        divider.pack(fill="x", padx=16, pady=(8, 0))
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)
        return frame, body

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Emisión de Factura Electrónica",
                      font=FONT_HEADING,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=4, pady=(0, 16))

        self._build_cliente_section()
        self._build_comprobante_section()
        self._build_detalles_section()
        self._build_resumen_section()
        self._build_acciones_section()

    def _field(self, parent, label, row=0, column=0):
        lbl = ctk.CTkLabel(parent, text=label, font=FONT_BODY,
                            text_color=COLOR_TEXT_SECONDARY)
        lbl.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=4)
        return lbl

    def _entry(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLOR_INPUT_BG)
        kwargs.setdefault("border_color", COLOR_INPUT_BORDER)
        kwargs.setdefault("text_color", COLOR_INPUT_TEXT)
        kwargs.setdefault("font", FONT_BODY)
        e = ctk.CTkEntry(parent, **kwargs)
        return e

    def _combo(self, parent, values, **kwargs):
        kwargs.setdefault("fg_color", COLOR_INPUT_BG)
        kwargs.setdefault("button_color", COLOR_GRADIENT_A)
        kwargs.setdefault("button_hover_color", COLOR_BUTTON_HOVER)
        kwargs.setdefault("text_color", COLOR_INPUT_TEXT)
        kwargs.setdefault("font", FONT_BODY)
        return ctk.CTkOptionMenu(parent, values=values, **kwargs)

    def _btn(self, parent, text, command=None, **kwargs):
        kwargs.setdefault("fg_color", COLOR_BUTTON_PRIMARY)
        kwargs.setdefault("hover_color", COLOR_BUTTON_HOVER)
        kwargs.setdefault("text_color", "white")
        kwargs.setdefault("font", FONT_BODY)
        kwargs.setdefault("corner_radius", 8)
        return ctk.CTkButton(parent, text=text, command=command, **kwargs)

    def _build_cliente_section(self):
        card, body = self._card(self, "Datos del Cliente")
        card.pack(fill="x", pady=(0, 12))
        body.grid_columnconfigure((1, 3), weight=1)

        self._field(body, "CUIT / DNI", 0, 0)
        cuit_frame = ctk.CTkFrame(body, fg_color="transparent")
        cuit_frame.grid(row=0, column=1, sticky="ew", pady=2)
        cuit_frame.grid_columnconfigure(0, weight=1)
        self.cuit_entry = self._entry(cuit_frame, placeholder_text="20-12345678-9")
        self.cuit_entry.grid(row=0, column=0, sticky="ew")
        self.cuit_entry.bind("<KeyRelease>", self._on_cuit_change)
        ctk.CTkButton(cuit_frame, text="Buscar", width=60,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER,
                       corner_radius=6,
                       command=self._buscar_cliente).grid(row=0, column=1, padx=(6, 0))

        self._field(body, "Razón Social", 0, 2)
        self.rs_entry = self._entry(body, placeholder_text="Razón Social")
        self.rs_entry.grid(row=0, column=3, sticky="ew", pady=2)

        self._field(body, "Condición IVA", 1, 0)
        self.cond_iva_combo = self._combo(body, [
            "Responsable Inscripto", "Exento", "Consumidor Final",
            "Monotributista", "No Categorizado",
        ])
        self.cond_iva_combo.grid(row=1, column=1, sticky="ew", pady=2)
        self.cond_iva_combo.set("Consumidor Final")

        self._field(body, "Domicilio", 1, 2)
        self.dom_entry = self._entry(body, placeholder_text="Domicilio")
        self.dom_entry.grid(row=1, column=3, sticky="ew", pady=2)

    def _build_comprobante_section(self):
        card, body = self._card(self, "Datos del Comprobante")
        card.pack(fill="x", pady=(0, 12))
        body.grid_columnconfigure((1, 3), weight=1)

        self._field(body, "Tipo", 0, 0)
        self.tipo_combo = self._combo(body, list(self.TIPOS_COMPROBANTE.keys()),
                                       command=self._on_tipo_change)
        self.tipo_combo.grid(row=0, column=1, sticky="ew", pady=2)
        self.tipo_combo.set("Factura C (Monotributo)")

        self._field(body, "Punto Venta", 0, 2)
        self.pv_entry = self._entry(body, placeholder_text="1", width=80)
        self.pv_entry.grid(row=0, column=3, sticky="w", pady=2)
        self.pv_entry.insert(0, str(self.settings.arca_punto_venta))

        self._field(body, "Concepto", 1, 0)
        self.concepto_combo = self._combo(
            body, ["PRODUCTOS", "SERVICIOS", "PRODUCTOS Y SERVICIOS"]
        )
        self.concepto_combo.grid(row=1, column=1, sticky="ew", pady=2)

        self._field(body, "Moneda", 1, 2)
        self.moneda_combo = self._combo(body, ["ARS", "USD", "EUR", "BRL"],
                                         command=self._on_moneda_change)
        self.moneda_combo.grid(row=1, column=3, sticky="w", pady=2)
        self.moneda_combo.set("ARS")

        self._field(body, "Observaciones", 2, 0)
        self.obs_text = ctk.CTkTextbox(
            body, height=50,
            fg_color=COLOR_INPUT_BG, border_color=COLOR_INPUT_BORDER,
            border_width=1, text_color=COLOR_INPUT_TEXT, font=FONT_BODY,
        )
        self.obs_text.grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)

    def _build_detalles_section(self):
        card, body = self._card(self, "Detalles de la Factura")
        card.pack(fill="both", expand=True, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        columns = ("#", "Código", "Descripción", "Cantidad", "P.Unit.", "IVA%", "Subtotal")
        self.tree = ttk.Treeview(body, columns=columns, show="headings", height=6)
        for col in columns:
            self.tree.heading(col, text=col)
            widths = {"#": 30, "Código": 80, "Descripción": 250,
                      "Cantidad": 70, "P.Unit.": 90, "IVA%": 50, "Subtotal": 100}
            self.tree.column(col, width=widths.get(col, 100), anchor="center")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#0D0D1F", foreground="#FFFFFF",
                        fieldbackground="#0D0D1F", borderwidth=0,
                        font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background="#1A1A3E", foreground="#FFFFFF",
                        borderwidth=0, font=(FONT_FAMILY, 10, "bold"))
        style.map("Treeview", background=[("selected", "#6C3CE1")])

        self.tree.grid(row=0, column=0, sticky="nsew", padx=0)
        self.tree.bind("<Double-1>", self._on_detalle_doble_click)

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=(8, 0))
        self._btn(btn_frame, "Agregar Item",
                   command=self._agregar_item).pack(side="left", padx=4)
        self._btn(btn_frame, "Eliminar Item",
                   command=self._eliminar_item).pack(side="left", padx=4)
        self._btn(btn_frame, "Buscar Producto",
                   command=self._buscar_producto).pack(side="left", padx=4)

    def _build_resumen_section(self):
        card, body = self._card(self, "Resumen")
        card.pack(fill="x", pady=(0, 12))
        body.grid_columnconfigure((1, 3, 5), weight=1)

        self._field(body, "Subtotal:", 0, 0)
        self.subtotal_label = ctk.CTkLabel(body, text="$ 0,00",
                                            font=(FONT_FAMILY, 14, "bold"),
                                            text_color=COLOR_TEXT_SECONDARY)
        self.subtotal_label.grid(row=0, column=1, sticky="w", pady=2)

        self._field(body, "IVA:", 0, 2)
        self.iva_label = ctk.CTkLabel(body, text="$ 0,00",
                                       font=(FONT_FAMILY, 14, "bold"),
                                       text_color=COLOR_TEXT_SECONDARY)
        self.iva_label.grid(row=0, column=3, sticky="w", pady=2)

        self._field(body, "TOTAL:", 0, 4)
        self.total_label = ctk.CTkLabel(body, text="$ 0,00",
                                         font=(FONT_FAMILY, 20, "bold"),
                                         text_color=COLOR_GREEN)
        self.total_label.grid(row=0, column=5, sticky="w", pady=2)

    def _build_acciones_section(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(frame, text="GENERAR FACTURA",
                       command=self.generar_factura,
                       width=250, height=48,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER,
                       font=(FONT_FAMILY, 14, "bold"),
                       corner_radius=10).pack(side="right", padx=4)

        ctk.CTkButton(frame, text="Guardar Borrador",
                       command=self._guardar_borrador,
                       width=150, height=40,
                       fg_color="transparent",
                       border_color=COLOR_CARD_BORDER,
                       border_width=1,
                       hover_color=COLOR_WHITE_5,
                       text_color=COLOR_TEXT_SECONDARY,
                       font=FONT_BODY).pack(side="right", padx=4)

        ctk.CTkButton(frame, text="Limpiar",
                       command=self.limpiar_formulario,
                       width=120, height=40,
                       fg_color="transparent",
                       border_color=COLOR_CARD_BORDER,
                       border_width=1,
                       hover_color=COLOR_WHITE_5,
                       text_color=COLOR_TEXT_SECONDARY,
                       font=FONT_BODY).pack(side="left", padx=4)

        self.status_label = ctk.CTkLabel(frame, text="",
                                          font=FONT_SMALL,
                                          text_color=COLOR_TEXT_MUTED)
        self.status_label.pack(side="left", padx=16)

    def _on_cuit_change(self, event=None):
        cuit = self.cuit_entry.get().replace("-", "").replace(" ", "")
        if len(cuit) == 11:
            valido, msg = ARCAValidators.validar_cuit(cuit)
            if valido:
                self.cuit_entry.configure(border_color=COLOR_GREEN)
                self._autocompletar_cliente(cuit)
            else:
                self.cuit_entry.configure(border_color=COLOR_RED)
        else:
            self.cuit_entry.configure(border_color=COLOR_INPUT_BORDER)

    def _buscar_cliente(self):
        query = self.cuit_entry.get().strip()
        if not query:
            query = self.rs_entry.get().strip()
        if not query:
            messagebox.showinfo("Buscar", "Ingrese CUIT o Razon Social")
            return

        session = self.session_factory()
        try:
            repo = ContribuyenteRepository(session)
            resultados = repo.search(query)
            if not resultados:
                messagebox.showinfo("Buscar", "Cliente no encontrado.\nComplete manualmente.")
                return
            if len(resultados) == 1:
                self._seleccionar_cliente(resultados[0])
            else:
                self._mostrar_lista_clientes(resultados)
        finally:
            session.close()

    def _autocompletar_cliente(self, cuit: str):
        session = self.session_factory()
        try:
            repo = ContribuyenteRepository(session)
            cliente = repo.get_by_cuit(cuit)
            if cliente:
                self._seleccionar_cliente(cliente)
        finally:
            session.close()

    def _seleccionar_cliente(self, cliente):
        self.cuit_entry.delete(0, "end")
        self.cuit_entry.insert(0, Formatters.formatear_cuit(cliente.cuit))
        self.rs_entry.delete(0, "end")
        self.rs_entry.insert(0, cliente.razon_social)
        cond_map = {1: "Responsable Inscripto", 5: "Consumidor Final",
                     6: "Monotributista", 3: "Exento", 7: "No Categorizado"}
        self.cond_iva_combo.set(cond_map.get(cliente.condicion_iva, "Consumidor Final"))
        self.dom_entry.delete(0, "end")
        if cliente.domicilio:
            self.dom_entry.insert(0, cliente.domicilio)

    def _mostrar_lista_clientes(self, clientes):
        top = ctk.CTkToplevel(self)
        top.title("Seleccionar Cliente")
        top.geometry("600x400")
        top.transient(self)
        top.grab_set()
        top.configure(fg_color=COLOR_BG)

        columns = ("CUIT", "Razon Social", "Condicion IVA", "Domicilio")
        tree = ttk.Treeview(top, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for c in clientes:
            cond = Formatters.condicion_iva_descripcion(c.condicion_iva)
            tree.insert("", "end", values=(
                Formatters.formatear_cuit(c.cuit), c.razon_social,
                cond, c.domicilio or ""
            ))

        def seleccionar():
            sel = tree.selection()
            if sel:
                item = tree.item(sel[0])
                cuit = item["values"][0].replace("-", "")
                session = self.session_factory()
                try:
                    repo = ContribuyenteRepository(session)
                    cliente = repo.get_by_cuit(cuit)
                    if cliente:
                        self._seleccionar_cliente(cliente)
                finally:
                    session.close()
                top.destroy()

        tree.bind("<Double-1>", lambda e: seleccionar())
        ctk.CTkButton(top, text="Seleccionar", command=seleccionar,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER).pack(pady=5)

    def _on_tipo_change(self, choice):
        pass

    def _on_moneda_change(self, choice):
        if choice != "ARS":
            self._actualizar_cotizacion()

    def _actualizar_cotizacion(self):
        def task():
            try:
                import httpx
                response = httpx.get(
                    self.settings.moneda_cotizacion_api, timeout=5
                )
                if response.is_success:
                    data = response.json()
                    cotiz = data.get("venta", data.get("oficial", 1))
                    self.after(0, lambda: self.status_label.configure(
                        text=f"Cotizacion USD: ${cotiz}"
                    ))
            except Exception:
                pass
        Thread(target=task, daemon=True).start()

    def _agregar_item(self):
        dialog = ItemDialog(self, "Agregar Item")
        self.wait_window(dialog)
        if dialog.resultado:
            self.detalles.append(dialog.resultado)
            self._actualizar_tree()

    def _eliminar_item(self):
        sel = self.tree.selection()
        if sel:
            idx = int(self.tree.item(sel[0])["values"][0]) - 1
            if 0 <= idx < len(self.detalles):
                del self.detalles[idx]
                self._actualizar_tree()

    def _on_detalle_doble_click(self, event):
        sel = self.tree.selection()
        if sel:
            idx = int(self.tree.item(sel[0])["values"][0]) - 1
            if 0 <= idx < len(self.detalles):
                dialog = ItemDialog(self, "Editar Item", self.detalles[idx])
                self.wait_window(dialog)
                if dialog.resultado:
                    self.detalles[idx] = dialog.resultado
                    self._actualizar_tree()

    def _buscar_producto(self):
        session = self.session_factory()
        try:
            repo = ProductoRepository(session)
            productos = repo.search("")

            if not productos:
                messagebox.showinfo("Productos", "No hay productos registrados")
                return

            top = ctk.CTkToplevel(self)
            top.title("Seleccionar Producto")
            top.geometry("600x400")
            top.transient(self)
            top.grab_set()
            top.configure(fg_color=COLOR_BG)

            columns = ("Codigo", "Descripcion", "Precio", "IVA%", "Tipo")
            tree = ttk.Treeview(top, columns=columns, show="headings")
            for col in columns:
                tree.heading(col, text=col)
            tree.pack(fill="both", expand=True, padx=10, pady=10)

            for p in productos:
                tree.insert("", "end", values=(
                    p.codigo, p.descripcion,
                    Formatters.formatear_importe(p.precio_base),
                    f"{p.alicuota_iva:.0f}%", p.tipo
                ))

            def seleccionar():
                sel = tree.selection()
                if sel:
                    item = tree.item(sel[0])
                    codigo = item["values"][0]
                    session2 = self.session_factory()
                    try:
                        repo2 = ProductoRepository(session2)
                        prod = repo2.get_by_codigo(codigo)
                        if prod:
                            det = {
                                "codigo": prod.codigo,
                                "descripcion": prod.descripcion,
                                "cantidad": 1.0,
                                "precio_unitario": prod.precio_base,
                                "alicuota_iva": prod.alicuota_iva,
                            }
                            self.detalles.append(det)
                            self._actualizar_tree()
                    finally:
                        session2.close()
                    top.destroy()

            tree.bind("<Double-1>", lambda e: seleccionar())
            ctk.CTkButton(top, text="Seleccionar", command=seleccionar,
                           fg_color=COLOR_BUTTON_PRIMARY,
                           hover_color=COLOR_BUTTON_HOVER).pack(pady=5)
        finally:
            session.close()

    def _actualizar_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        subtotal = 0.0
        iva_total = 0.0

        for i, det in enumerate(self.detalles):
            sub = det["cantidad"] * det["precio_unitario"]
            iva = sub * det["alicuota_iva"] / 100
            subtotal += sub
            iva_total += iva

            self.tree.insert("", "end", values=(
                i + 1,
                det.get("codigo", ""),
                det["descripcion"][:50],
                det["cantidad"],
                Formatters.formatear_importe(det["precio_unitario"]),
                f"{det['alicuota_iva']:.0f}",
                Formatters.formatear_importe(sub),
            ))

        self.subtotal_label.configure(text=Formatters.formatear_importe(subtotal))
        self.iva_label.configure(text=Formatters.formatear_importe(iva_total))
        self.total_label.configure(text=Formatters.formatear_importe(subtotal + iva_total))

    def generar_factura(self):
        try:
            data = self._recoger_datos()
        except ValidationError as e:
            messagebox.showerror("Error de Validacion", str(e))
            return

        if not self.detalles:
            messagebox.showwarning("Validacion", "Debe agregar al menos un item")
            return

        self.status_label.configure(text="Generando factura...")
        self._set_buttons_state("disabled")

        def task():
            try:
                resultado = self.facturador.emitir_factura(data)
                self.after(0, self._procesar_resultado, resultado)
            except Exception as e:
                self.after(0, lambda: (
                    messagebox.showerror("Error", f"Error al generar factura: {e}"),
                    self._set_buttons_state("normal"),
                ))

        Thread(target=task, daemon=True).start()

    def _recoger_datos(self) -> Dict[str, Any]:
        tipo_map = {"Responsable Inscripto": 1, "Exento": 3,
                    "Consumidor Final": 5, "Monotributista": 6,
                    "No Categorizado": 7}

        cuit = self.cuit_entry.get().replace("-", "").replace(" ", "")
        valido, msg = ARCAValidators.validar_cuit(cuit)
        if not valido:
            raise ValidationError(f"CUIT cliente invalido: {msg}")

        return {
            "tipo_comprobante": self.TIPOS_COMPROBANTE[self.tipo_combo.get()],
            "punto_venta": int(self.pv_entry.get()),
            "cuit_cliente": cuit,
            "razon_social_cliente": self.rs_entry.get().strip(),
            "condicion_iva_cliente": tipo_map.get(self.cond_iva_combo.get(), 5),
            "domicilio_cliente": self.dom_entry.get().strip(),
            "concepto": self.concepto_combo.get(),
            "moneda": self.moneda_combo.get(),
            "cotizacion": 1.0,
            "detalles": [{
                "codigo_producto": d.get("codigo", ""),
                "descripcion": d["descripcion"],
                "cantidad": d["cantidad"],
                "precio_unitario": d["precio_unitario"],
                "alicuota_iva": d["alicuota_iva"],
                "bonificacion": d.get("bonificacion", 0),
            } for d in self.detalles],
            "observaciones": self.obs_text.get("0.0", "end").strip(),
        }

    def _procesar_resultado(self, resultado):
        self._set_buttons_state("normal")

        if resultado.success:
            tipo_desc = Formatters.tipo_comprobante_descripcion(
                self.TIPOS_COMPROBANTE[self.tipo_combo.get()]
            )
            messagebox.showinfo(
                "Factura Generada",
                f"Factura emitida exitosamente!\n\n"
                f"CAE: {Formatters.formatear_cae(resultado.cae or '')}\n"
                f"Vencimiento CAE: {resultado.cae_vencimiento.strftime('%d/%m/%Y') if resultado.cae_vencimiento else 'N/A'}\n"
                f"Tipo: {tipo_desc}\n"
                f"Numero: {resultado.numero_factura}\n\n"
                f"Desea generar el PDF?",
            )
            self.status_label.configure(
                text=f"Factura emitida - CAE: {resultado.cae}",
                text_color=COLOR_GREEN,
            )
            self._preguntar_pdf(resultado)
            self.limpiar_formulario()
        else:
            messagebox.showerror(
                "Error",
                f"No se pudo emitir la factura:\n\n{resultado.error_message}\n\n"
                + (f"Codigo: {resultado.error_code}" if resultado.error_code else "")
            )
            self.status_label.configure(
                text=f"Error: {resultado.error_message[:50]}...",
                text_color=COLOR_RED,
            )

    def _preguntar_pdf(self, resultado):
        if messagebox.askyesno("PDF", "Desea generar el PDF de la factura?"):
            session = self.session_factory()
            try:
                repo = FacturaRepository(session)
                factura = repo.get_by_id(resultado.factura_id)
                if factura:
                    from reports.pdf_generator import generate_factura_pdf
                    factura_data = {
                        "tipo_comprobante": factura.tipo_comprobante,
                        "punto_venta": factura.punto_venta,
                        "numero_factura": factura.numero_factura,
                        "cae": factura.cae,
                        "cae_vencimiento": factura.cae_vencimiento,
                        "fecha_emision": factura.fecha_emision,
                        "cuit_cliente": factura.cuit_cliente,
                        "razon_social_cliente": factura.razon_social_cliente,
                        "condicion_iva_cliente": factura.condicion_iva_cliente,
                        "domicilio_cliente": factura.domicilio_cliente,
                        "subtotal": factura.subtotal,
                        "iva_total": factura.iva_total,
                        "total": factura.total,
                        "detalles": [
                            {
                                "descripcion": d.descripcion,
                                "cantidad": d.cantidad,
                                "precio_unitario": d.precio_unitario,
                                "alicuota_iva": d.alicuota_iva,
                                "subtotal": d.subtotal,
                            }
                            for d in factura.detalles
                        ],
                        "observaciones": factura.observaciones,
                    }
                    from tkinter import filedialog
                    import os
                    filename = f"Factura_{factura.tipo_comprobante}_{factura.punto_venta:04d}-{factura.numero_factura:08d}.pdf"
                    filepath = filedialog.asksaveasfilename(
                        defaultextension=".pdf",
                        filetypes=[("PDF files", "*.pdf")],
                        initialfile=filename,
                    )
                    if filepath:
                        generate_factura_pdf(factura_data, filepath)
                        messagebox.showinfo("PDF", f"PDF generado:\n{filepath}")
                        os.startfile(filepath)
            finally:
                session.close()

    def _guardar_borrador(self):
        try:
            data = self._recoger_datos()
            data["estado"] = "BORRADOR"
            session = self.session_factory()
            try:
                repo = FacturaRepository(session)
                detalles = data.pop("detalles", [])
                factura = repo.create(data, detalles)
                session.commit()
                messagebox.showinfo("Borrador", f"Borrador guardado (ID: {factura.id})")
            finally:
                session.close()
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando borrador: {e}")

    def limpiar_formulario(self):
        self.cuit_entry.delete(0, "end")
        self.rs_entry.delete(0, "end")
        self.dom_entry.delete(0, "end")
        self.cond_iva_combo.set("Consumidor Final")
        self.obs_text.delete("0.0", "end")
        self.detalles = []
        self._actualizar_tree()
        self.status_label.configure(text="")

    def _set_buttons_state(self, state):
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(state=state)

    def actualizar_facturador(self, facturador):
        self.facturador = facturador

    def on_activate(self):
        pass


class ItemDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, item: Optional[Dict] = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x350")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLOR_BG)
        self.resultado: Optional[Dict] = None

        self._build_ui()
        if item:
            self._cargar_item(item)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Código (opcional):",
                      text_color=COLOR_TEXT_SECONDARY).grid(
            row=0, column=0, padx=12, pady=6, sticky="w"
        )
        self.codigo_entry = ctk.CTkEntry(self, fg_color=COLOR_INPUT_BG,
                                          border_color=COLOR_INPUT_BORDER,
                                          text_color=COLOR_INPUT_TEXT)
        self.codigo_entry.grid(row=0, column=1, padx=12, pady=6, sticky="ew")

        ctk.CTkLabel(self, text="Descripción:",
                      text_color=COLOR_TEXT_SECONDARY).grid(
            row=1, column=0, padx=12, pady=6, sticky="w"
        )
        self.desc_entry = ctk.CTkEntry(self, fg_color=COLOR_INPUT_BG,
                                        border_color=COLOR_INPUT_BORDER,
                                        text_color=COLOR_INPUT_TEXT)
        self.desc_entry.grid(row=1, column=1, padx=12, pady=6, sticky="ew")

        ctk.CTkLabel(self, text="Cantidad:",
                      text_color=COLOR_TEXT_SECONDARY).grid(
            row=2, column=0, padx=12, pady=6, sticky="w"
        )
        self.cant_spinbox = ctk.CTkEntry(self, placeholder_text="1",
                                          fg_color=COLOR_INPUT_BG,
                                          border_color=COLOR_INPUT_BORDER,
                                          text_color=COLOR_INPUT_TEXT)
        self.cant_spinbox.grid(row=2, column=1, padx=12, pady=6, sticky="ew")
        self.cant_spinbox.insert(0, "1")

        ctk.CTkLabel(self, text="Precio Unitario:",
                      text_color=COLOR_TEXT_SECONDARY).grid(
            row=3, column=0, padx=12, pady=6, sticky="w"
        )
        self.precio_entry = ctk.CTkEntry(self, fg_color=COLOR_INPUT_BG,
                                          border_color=COLOR_INPUT_BORDER,
                                          text_color=COLOR_INPUT_TEXT)
        self.precio_entry.grid(row=3, column=1, padx=12, pady=6, sticky="ew")

        ctk.CTkLabel(self, text="Alicuota IVA:",
                      text_color=COLOR_TEXT_SECONDARY).grid(
            row=4, column=0, padx=12, pady=6, sticky="w"
        )
        self.iva_combo = ctk.CTkOptionMenu(
            self, values=["0.0%", "10.5%", "21.0%", "27.0%", "5.0%", "2.5%"],
            fg_color=COLOR_INPUT_BG, button_color=COLOR_GRADIENT_A,
            button_hover_color=COLOR_BUTTON_HOVER, text_color=COLOR_INPUT_TEXT,
        )
        self.iva_combo.grid(row=4, column=1, padx=12, pady=6, sticky="w")
        self.iva_combo.set("21.0%")

        ctk.CTkButton(self, text="Aceptar", command=self._aceptar,
                       width=200, height=44,
                       fg_color=COLOR_GRADIENT_A,
                       hover_color=COLOR_BUTTON_HOVER,
                       font=(FONT_FAMILY, 13, "bold"),
                       corner_radius=8).grid(row=5, column=0, columnspan=2, pady=16)

    def _cargar_item(self, item: Dict):
        self.codigo_entry.insert(0, item.get("codigo", ""))
        self.desc_entry.insert(0, item.get("descripcion", ""))
        self.cant_spinbox.delete(0, "end")
        self.cant_spinbox.insert(0, str(item.get("cantidad", 1)))
        self.precio_entry.insert(0, str(item.get("precio_unitario", 0)))
        self.iva_combo.set(f"{item.get('alicuota_iva', 21):.1f}%")

    def _aceptar(self):
        desc = self.desc_entry.get().strip()
        if not desc:
            messagebox.showerror("Validacion", "La descripcion es requerida")
            return

        try:
            cant = float(self.cant_spinbox.get())
            if cant <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Validacion", "Cantidad invalida")
            return

        try:
            precio = float(self.precio_entry.get().replace(",", "."))
            if precio < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Validacion", "Precio invalido")
            return

        iva = float(self.iva_combo.get().replace("%", "").replace(",", "."))

        self.resultado = {
            "codigo": self.codigo_entry.get().strip(),
            "descripcion": desc,
            "cantidad": cant,
            "precio_unitario": precio,
            "alicuota_iva": iva,
        }
        self.destroy()
