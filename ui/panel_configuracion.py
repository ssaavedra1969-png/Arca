from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import ConfigManager
from core.auth import Authenticator, CertificateManager
from utils.formatters import Formatters
from loguru import logger
from ui.style import *


class PanelConfiguracion(ctk.CTkFrame):
    def __init__(self, parent, settings, authenticator: Optional[Authenticator],
                 on_updated: Optional[Callable] = None):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings
        self.authenticator = authenticator
        self.on_updated = on_updated
        self.cert_info = {}

        self._build_ui()
        self._cargar_configuracion()

    def _card(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=12,
                              border_width=1, border_color=COLOR_CARD_BORDER)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(header, text=title, font=FONT_SECTION,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        divider = ctk.CTkFrame(frame, fg_color=COLOR_WHITE_10, height=1)
        divider.pack(fill="x", padx=16, pady=(8, 0))
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)
        return frame, body

    def _entry(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLOR_INPUT_BG)
        kwargs.setdefault("border_color", COLOR_INPUT_BORDER)
        kwargs.setdefault("text_color", COLOR_INPUT_TEXT)
        kwargs.setdefault("font", FONT_BODY)
        return ctk.CTkEntry(parent, **kwargs)

    def _field(self, parent, label, row=0, column=0):
        lbl = ctk.CTkLabel(parent, text=label, font=FONT_BODY,
                            text_color=COLOR_TEXT_SECONDARY)
        lbl.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=4)
        return lbl

    def _build_ui(self):
        ctk.CTkLabel(self, text="Configuración del Sistema",
                      font=FONT_HEADING,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=4, pady=(0, 16))

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(main_frame, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(main_frame, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._seccion_certificados(left)
        self._seccion_generales(right)
        self._seccion_acciones(right)

    def _seccion_certificados(self, parent):
        card, body = self._card(parent, "Certificados Digitales")
        card.pack(fill="x")

        self._field(body, "Archivo Certificado (.crt):", 0, 0)
        cert_frame = ctk.CTkFrame(body, fg_color="transparent")
        cert_frame.grid(row=0, column=1, sticky="ew", pady=2)
        cert_frame.grid_columnconfigure(0, weight=1)
        self.cert_file_var = ctk.StringVar()
        self._entry(cert_frame, textvariable=self.cert_file_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ctk.CTkButton(cert_frame, text="Examinar", width=80,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER,
                       corner_radius=6,
                       command=lambda: self._seleccionar_archivo("cert")).grid(
            row=0, column=1
        )

        self._field(body, "Archivo Clave Privada (.key):", 1, 0)
        key_frame = ctk.CTkFrame(body, fg_color="transparent")
        key_frame.grid(row=1, column=1, sticky="ew", pady=2)
        key_frame.grid_columnconfigure(0, weight=1)
        self.key_file_var = ctk.StringVar()
        self._entry(key_frame, textvariable=self.key_file_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ctk.CTkButton(key_frame, text="Examinar", width=80,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER,
                       corner_radius=6,
                       command=lambda: self._seleccionar_archivo("key")).grid(
            row=0, column=1
        )

        self._field(body, "PIN Clave Privada:", 2, 0)
        self.pin_var = ctk.StringVar()
        self._entry(body, textvariable=self.pin_var, show="*").grid(
            row=2, column=1, sticky="ew", pady=2
        )

        info_card = ctk.CTkFrame(body, fg_color="#0A0A1A", corner_radius=8,
                                  border_width=1, border_color=COLOR_CARD_BORDER)
        info_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.cert_info_label = ctk.CTkLabel(
            info_card, text="Certificado no cargado",
            font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, justify="left"
        )
        self.cert_info_label.pack(padx=12, pady=8, anchor="w")

        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        ctk.CTkButton(btn_frame, text="Validar Certificado",
                       fg_color=COLOR_GRADIENT_A,
                       hover_color=COLOR_BUTTON_HOVER,
                       corner_radius=6, font=FONT_BODY,
                       command=self._validar_certificado).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Ver Información",
                       fg_color="transparent",
                       border_color=COLOR_CARD_BORDER, border_width=1,
                       hover_color=COLOR_WHITE_5,
                       text_color=COLOR_TEXT_SECONDARY,
                       corner_radius=6, font=FONT_BODY,
                       command=self._ver_info_certificado).pack(side="left", padx=4)

    def _seccion_arca(self, parent):
        card, body = self._card(parent, "Configuración ARCA")
        card.pack(fill="x", pady=(12, 0))
        body.grid_columnconfigure(1, weight=1)

        self._field(body, "CUIT Emisor:", 0, 0)
        self.cuit_var = ctk.StringVar()
        self._entry(body, textvariable=self.cuit_var,
                     placeholder_text="20345678901").grid(row=0, column=1, sticky="ew", pady=2)

        self._field(body, "Punto de Venta:", 1, 0)
        self.pv_var = ctk.StringVar(value="1")
        self._entry(body, textvariable=self.pv_var,
                     placeholder_text="1-9999").grid(row=1, column=1, sticky="ew", pady=2)

        self._field(body, "Tema:", 2, 0)
        self.tema_var = ctk.StringVar(value="dark")
        ctk.CTkOptionMenu(body, values=["dark", "light"],
                           variable=self.tema_var,
                           fg_color=COLOR_INPUT_BG,
                           button_color=COLOR_GRADIENT_A,
                           button_hover_color=COLOR_BUTTON_HOVER,
                           text_color=COLOR_INPUT_TEXT).grid(row=2, column=1, sticky="w", pady=2)

        row = 3
        self.homo_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(body, text="Modo Homologación (Pruebas)",
                       variable=self.homo_var,
                       button_color=COLOR_GRADIENT_A,
                       progress_color=COLOR_GRADIENT_A,
                       font=FONT_BODY).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=4
        )

    def _seccion_generales(self, parent):
        card, body = self._card(parent, "Configuración General")
        card.pack(fill="x")
        body.grid_columnconfigure(1, weight=1)

        self._field(body, "Moneda por defecto:", 0, 0)
        self.moneda_var = ctk.StringVar(value="ARS")
        ctk.CTkOptionMenu(body, values=["ARS", "USD", "EUR", "BRL"],
                           variable=self.moneda_var,
                           fg_color=COLOR_INPUT_BG,
                           button_color=COLOR_GRADIENT_A,
                           button_hover_color=COLOR_BUTTON_HOVER,
                           text_color=COLOR_INPUT_TEXT).grid(row=0, column=1, sticky="w", pady=2)

        self._field(body, "Logo para Facturas:", 1, 0)
        self.logo_var = ctk.StringVar()
        logo_frame = ctk.CTkFrame(body, fg_color="transparent")
        logo_frame.grid(row=1, column=1, sticky="ew", pady=2)
        logo_frame.grid_columnconfigure(0, weight=1)
        self._entry(logo_frame, textvariable=self.logo_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ctk.CTkButton(logo_frame, text="Examinar", width=80,
                       fg_color=COLOR_BUTTON_PRIMARY,
                       hover_color=COLOR_BUTTON_HOVER,
                       corner_radius=6,
                       command=self._seleccionar_logo).grid(row=0, column=1)

    def _seccion_acciones(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(16, 0))

        ctk.CTkButton(frame, text="Guardar Configuración",
                       command=self._guardar_configuracion,
                       width=200, height=44,
                       fg_color=COLOR_GRADIENT_A,
                       hover_color=COLOR_BUTTON_HOVER,
                       font=(FONT_FAMILY, 13, "bold"),
                       corner_radius=8).pack(side="left", padx=4)

        ctk.CTkButton(frame, text="Test Conexión ARCA",
                       command=self._test_conexion,
                       width=200, height=44,
                       fg_color="transparent",
                       border_color=COLOR_CARD_BORDER,
                       border_width=1,
                       hover_color=COLOR_WHITE_5,
                       text_color=COLOR_TEXT_SECONDARY,
                       font=FONT_BODY,
                       corner_radius=8).pack(side="left", padx=4)

    def _seleccionar_archivo(self, tipo: str):
        if tipo == "cert":
            path = filedialog.askopenfilename(
                title="Seleccionar Certificado",
                filetypes=[("Certificados", "*.crt;*.pem;*.cer"), ("Todos", "*.*")],
            )
            if path:
                self.cert_file_var.set(path)
                self._cargar_info_certificado()
        else:
            path = filedialog.askopenfilename(
                title="Seleccionar Clave Privada",
                filetypes=[("Claves", "*.key;*.pem"), ("Todos", "*.*")],
            )
            if path:
                self.key_file_var.set(path)

    def _seleccionar_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Logo",
            filetypes=[("Imagenes", "*.png;*.jpg;*.jpeg"), ("Todos", "*.*")],
        )
        if path:
            self.logo_var.set(path)

    def _cargar_info_certificado(self):
        cert_path = Path(self.cert_file_var.get())
        if not cert_path.exists():
            self.cert_info_label.configure(text="Archivo de certificado no encontrado",
                                            text_color=COLOR_RED)
            return

        try:
            cert_mgr = CertificateManager(
                cert_path,
                Path(self.key_file_var.get() or ""),
                self.pin_var.get() or None,
            )
            ok, msg = cert_mgr.load()
            if ok:
                info = cert_mgr.get_info()
                self.cert_info = info
                dias = info.get("days_remaining", 0)
                color = COLOR_GREEN if dias > 30 else (COLOR_ORANGE if dias > 7 else COLOR_RED)
                valido = info.get('valid_from')
                vence = info.get('valid_until')
                desde_str = valido.strftime('%d/%m/%Y') if isinstance(valido, datetime) else ''
                hasta_str = vence.strftime('%d/%m/%Y') if isinstance(vence, datetime) else ''
                self.cert_info_label.configure(
                    text=(f"Válido: {desde_str} - Vence: {hasta_str} | "
                          f"Días restantes: {dias} | "
                          f"Organización: {info.get('organization', 'N/A')}"),
                    text_color=color,
                )
            else:
                self.cert_info_label.configure(
                    text=f"Error: {msg}", text_color=COLOR_RED
                )
        except Exception as e:
            self.cert_info_label.configure(
                text=f"Error cargando certificado: {e}", text_color=COLOR_RED
            )

    def _validar_certificado(self):
        def task():
            try:
                cert_mgr = CertificateManager(
                    Path(self.cert_file_var.get()),
                    Path(self.key_file_var.get()),
                    self.pin_var.get() or None,
                )
                ok, msg = cert_mgr.load()
                if ok:
                    valido, vmsg = cert_mgr.validate()
                    self.after(0, lambda: (
                        messagebox.showinfo("Certificado", f"Certificado válido!\n\n{vmsg}")
                        if valido else
                        messagebox.showerror("Certificado", f"Certificado inválido:\n{vmsg}")
                    ))
                else:
                    self.after(0, lambda: messagebox.showerror(
                        "Error", f"Error cargando certificado: {msg}"
                    ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"Error: {e}"
                ))

        Thread(target=task, daemon=True).start()

    def _ver_info_certificado(self):
        if not self.cert_info:
            messagebox.showinfo("Info", "Cargue un certificado primero")
            return
        info = self.cert_info
        texto = (
            f"Sujeto: {info.get('subject', 'N/A')}\n"
            f"Organización: {info.get('organization', 'N/A')}\n"
            f"Emisor: {info.get('issuer', 'N/A')}\n"
            f"Válido desde: {self._fmt_fecha(info.get('valid_from'))}\n"
            f"Válido hasta: {self._fmt_fecha(info.get('valid_until'))}\n"
            f"Días restantes: {info.get('days_remaining', 0)}\n"
            f"Serial: {info.get('serial', 'N/A')}\n"
            f"Algoritmo: {info.get('signature_algorithm', 'N/A')}\n"
            f"Fingerprint SHA256: {str(info.get('fingerprint_sha256', ''))[:32]}..."
        )
        messagebox.showinfo("Información del Certificado", texto)

    def _test_conexion(self):
        def task():
            try:
                from core.auth import Authenticator
                auth = Authenticator(self.settings)
                auth.initialize()
                ok, msg = auth.test_connection()
                self.after(0, lambda: (
                    messagebox.showinfo("Conexión", f"OK: {msg}")
                    if ok else messagebox.showerror("Conexión", f"Error: {msg}")
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Conexión", f"Error: {e}"
                ))

        Thread(target=task, daemon=True).start()

    def _guardar_configuracion(self):
        self.settings.arca_cert_file = self.cert_file_var.get()
        self.settings.arca_key_file = self.key_file_var.get()
        self.settings.arca_cert_pin = self.pin_var.get()
        self.settings.arca_cuit = int(self.cuit_var.get().replace("-", ""))
        self.settings.arca_punto_venta = int(self.pv_var.get())
        self.settings.arca_homo = self.homo_var.get()
        self.settings.moneda_defecto = self.moneda_var.get()
        self.settings.report_logo = self.logo_var.get()

        if self.on_updated:
            self.on_updated()
        else:
            messagebox.showinfo("Configuración", "Configuración guardada")

    def _cargar_configuracion(self):
        self.cert_file_var.set(self.settings.arca_cert_file)
        self.key_file_var.set(self.settings.arca_key_file)
        self.pin_var.set(self.settings.arca_cert_pin)
        self.cuit_var.set(str(self.settings.arca_cuit))
        self.pv_var.set(str(self.settings.arca_punto_venta))
        self.homo_var.set(self.settings.arca_homo)
        self.moneda_var.set(self.settings.moneda_defecto)
        self.logo_var.set(self.settings.report_logo)

        if Path(self.settings.arca_cert_file).exists():
            self._cargar_info_certificado()

    @staticmethod
    def _fmt_fecha(fecha):
        if isinstance(fecha, datetime):
            return fecha.strftime("%d/%m/%Y")
        return str(fecha)

    def on_activate(self):
        self._cargar_configuracion()
