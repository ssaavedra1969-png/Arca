import sys
import os
from pathlib import Path
from typing import Optional
from threading import Thread
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from config import ConfigManager
from utils.logger import LoggerManager
from utils.encryption import EncryptionManager, CredentialVault
from utils.exceptions import ARCAError
from utils.firebase_sync import firebase_sync
from database.models import get_session_factory, init_db
from core.auth import Authenticator
from core.facturador import Facturador, create_facturador

from ui.panel_configuracion import PanelConfiguracion
from ui.panel_facturacion import PanelFacturacion
from ui.panel_historial import PanelHistorial
from ui.panel_reportes import PanelReportes
from ui.style import *

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ARCAFacturadorApp(ctk.CTk):
    APP_NAME = "ARCA Facturador"
    VERSION = "1.0.0"

    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings or ConfigManager.load()
        self.session_factory = None
        self.enc_manager: Optional[EncryptionManager] = None
        self.vault: Optional[CredentialVault] = None
        self.authenticator: Optional[Authenticator] = None
        self.facturador: Optional[Facturador] = None
        self._current_panel = None
        self._nav_buttons = []

        self._setup_window()
        self._init_components()
        self._build_ui()
        self._bind_shortcuts()
        self._start_background_tasks()

    def _setup_window(self):
        self.title(f"{self.APP_NAME} v{self.VERSION}")
        self.geometry("1280x800")
        self.minsize(1024, 600)
        self.configure(fg=COLOR_BG)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        icon_path = Path(self.settings.resources_dir) / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _init_components(self):
        try:
            db_path = self.settings.get_db_path()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.session_factory = init_db(str(db_path))

            LoggerManager.setup(self.settings)

            from loguru import logger
            self.logger = logger

            self.authenticator = Authenticator(self.settings)
            self.facturador = Facturador(self.settings, self.authenticator)
            self.facturador.initialize(self.session_factory)

            self.logger.info("Componentes inicializados correctamente")
        except Exception as e:
            messagebox.showerror(
                "Error de Inicializacion",
                f"Error inicializando componentes:\n{e}\n\nVerifique la configuracion.",
            )

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, width=240,
                               border_width=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)

        brand_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(20, 16))

        logo_frame = ctk.CTkFrame(brand_frame, fg_color="transparent", width=40, height=40)
        logo_frame.pack(side="left", padx=(0, 12))
        logo_frame.pack_propagate(False)
        logo_canvas = tk.Canvas(logo_frame, width=40, height=40, bg=COLOR_BG,
                                 highlightthickness=0)
        logo_canvas.pack(fill="both", expand=True)
        logo_canvas.create_oval(0, 0, 40, 40, fill=COLOR_GRADIENT_A, outline="")
        logo_canvas.create_text(20, 20, text="F", fill="white",
                                 font=(FONT_FAMILY, 18, "bold"))

        text_frame = ctk.CTkFrame(brand_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_frame, text="FALPAT SRL", font=(FONT_FAMILY, 16, "bold"),
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(text_frame, text="ADMINISTRACION", font=(FONT_FAMILY, 8),
                      text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        divider = ctk.CTkFrame(sidebar, fg_color=COLOR_WHITE_10, height=1)
        divider.pack(fill="x", padx=16, pady=0)

        nav_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent",
                                             scrollbar_button_color=COLOR_GRADIENT_A)
        nav_frame.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        sections = [
            ("PRINCIPAL", [
                ("dashboard", "\u2302", "Dashboard"),
            ]),
            ("GESTION", [
                ("facturacion", "\u00A4", "Facturación"),
                ("historial", "\u2630", "Historial"),
                ("reportes", "\u2261", "Reportes"),
            ]),
            ("SISTEMA", [
                ("configuracion", "\u2699", "Configuración"),
            ]),
        ]

        for section_name, items in sections:
            ctk.CTkLabel(nav_frame, text=section_name,
                          font=(FONT_FAMILY, 9, "bold"),
                          text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=12, pady=(12, 4))

            for panel_id, icon, label in items:
                btn_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
                btn_frame.pack(fill="x", pady=1)

                btn = ctk.CTkButton(
                    btn_frame,
                    text=f"  {icon}  {label}",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=COLOR_WHITE_5,
                    text_color=COLOR_TEXT_SECONDARY,
                    font=(FONT_FAMILY, 13),
                    height=36,
                    corner_radius=10,
                    command=lambda pid=panel_id: self._switch_panel(pid),
                )
                btn.pack(fill="x")
                self._nav_buttons.append((panel_id, btn, btn_frame))

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 16))

        user_frame = ctk.CTkFrame(footer, fg_color="transparent")
        user_frame.pack(fill="x", pady=(8, 4))
        avatar = ctk.CTkFrame(user_frame, fg_color=COLOR_GRADIENT_A, width=32, height=32,
                               corner_radius=16)
        avatar.pack(side="left", padx=(0, 10))
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text="FS", font=(FONT_FAMILY, 10, "bold"),
                      text_color="white").pack(expand=True)
        ctk.CTkLabel(user_frame, text="FALPAT SRL\nAdministrador",
                      font=(FONT_FAMILY, 11), text_color=COLOR_TEXT_PRIMARY,
                      justify="left").pack(side="left")

    def _build_main_area(self):
        main_container = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        main_container.grid(row=0, column=1, rowspan=2, sticky="nsew")
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main_container, fg_color=COLOR_BG, height=48,
                               border_width=0)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 0))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text=self.APP_NAME,
                      font=(FONT_FAMILY, 18, "bold"),
                      text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, sticky="w")

        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.grid(row=0, column=2, sticky="e")
        self.status_indicator = ctk.CTkFrame(status_frame, fg_color=COLOR_GREEN,
                                              width=8, height=8, corner_radius=4)
        self.status_indicator.pack(side="left", padx=(0, 6))
        self.status_label = ctk.CTkLabel(status_frame, text="Conectado",
                                          font=(FONT_FAMILY, 11),
                                          text_color=COLOR_TEXT_SECONDARY)
        self.status_label.pack(side="left")

        ctk.CTkLabel(header, text=datetime.now().strftime("%d/%m/%Y"),
                      font=(FONT_FAMILY, 11),
                      text_color=COLOR_TEXT_MUTED).grid(row=0, column=3, padx=(20, 0))

        divider = ctk.CTkFrame(main_container, fg_color=COLOR_WHITE_10, height=1)
        divider.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

        self.content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        self.content_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.panels = {}

        welcome = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        welcome.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(welcome, text="Bienvenido al Sistema de Gestión",
                      font=(FONT_FAMILY, 24, "bold"),
                      text_color=COLOR_TEXT_PRIMARY).pack(expand=True)
        ctk.CTkLabel(welcome, text="Seleccione un módulo desde el panel lateral",
                      font=(FONT_FAMILY, 14),
                      text_color=COLOR_TEXT_MUTED).pack()
        self.panels["__welcome"] = welcome

        self._switch_panel("facturacion")

    def _build_panel(self, panel_id):
        if panel_id in self.panels and panel_id != "__welcome":
            return self.panels[panel_id]

        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent",
                                         scrollbar_button_color=COLOR_GRADIENT_A)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        if panel_id == "facturacion":
            panel = PanelFacturacion(scroll, self.settings, self.facturador,
                                     self.session_factory)
        elif panel_id == "historial":
            panel = PanelHistorial(scroll, self.settings, self.session_factory)
        elif panel_id == "reportes":
            panel = PanelReportes(scroll, self.settings, self.session_factory)
        elif panel_id == "configuracion":
            panel = PanelConfiguracion(scroll, self.settings, self.authenticator,
                                        self._on_config_updated)
        elif panel_id == "dashboard":
            panel = PanelDashboard(scroll, self.settings, self.session_factory,
                                    self.facturador)
        else:
            return None

        panel.pack(fill="both", expand=True)
        self.panels[panel_id] = (container, panel)
        return container

    def _switch_panel(self, panel_id):
        for _, btn, _ in self._nav_buttons:
            btn.configure(fg_color="transparent", text_color=COLOR_TEXT_SECONDARY)

        for pid, btn, _ in self._nav_buttons:
            if pid == panel_id:
                btn.configure(fg_color=COLOR_WHITE_5, text_color=COLOR_TEXT_PRIMARY)
                break

        for existing in self.content_frame.winfo_children():
            existing.grid_remove()

        container = self._build_panel(panel_id)
        if container:
            container.grid(row=0, column=0, sticky="nsew")
            if panel_id != "__welcome":
                _, panel = self.panels[panel_id]
                if hasattr(panel, 'on_activate'):
                    panel.on_activate()

    def _bind_shortcuts(self):
        self.bind("<F2>", lambda e: self._nueva_factura())
        self.bind("<F5>", lambda e: self._generar_factura())
        self.bind("<F12>", lambda e: self._abrir_historial())

    def _start_background_tasks(self):
        self._check_cert_expiry()

    def _check_cert_expiry(self):
        try:
            if self.authenticator and self.authenticator.is_cert_expiring_soon(7):
                self._show_notification(
                    "Certificado Proximo a Vencer",
                    "Su certificado digital vence en menos de 7 dias. "
                    "Renuevelo para evitar interrupciones.",
                    "warning",
                )
        except Exception:
            pass
        self.after(86400000, self._check_cert_expiry)

    def _nueva_factura(self):
        self._switch_panel("facturacion")
        if "facturacion" in self.panels:
            _, panel = self.panels["facturacion"]
            panel.limpiar_formulario()

    def _generar_factura(self):
        self._switch_panel("facturacion")
        if "facturacion" in self.panels:
            _, panel = self.panels["facturacion"]
            panel.generar_factura()

    def _abrir_historial(self):
        self._switch_panel("historial")
        if "historial" in self.panels:
            _, panel = self.panels["historial"]
            panel.cargar_datos()

    def _abrir_reportes(self):
        self._switch_panel("reportes")
        if "reportes" in self.panels:
            _, panel = self.panels["reportes"]
            panel.cargar_datos()

    def _on_config_updated(self):
        self.facturador = create_facturador(self.settings)
        if "facturacion" in self.panels:
            _, panel = self.panels["facturacion"]
            panel.actualizar_facturador(self.facturador)
        messagebox.showinfo("Configuracion", "Configuracion guardada correctamente")

    def _sincronizar_pendientes(self):
        if not self.facturador:
            messagebox.showwarning("Atencion", "Facturador no inicializado")
            return

        def task():
            try:
                exitos, fallos, errores = self.facturador.sincronizar_pendientes()
                self.after(0, lambda: messagebox.showinfo(
                    "Sincronizacion",
                    f"Sincronizacion completada:\n"
                    f"Exitos: {exitos}\nFallos: {fallos}\n"
                    + (f"\nErrores:\n" + "\n".join(errores[:5]) if errores else "")
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        Thread(target=task, daemon=True).start()

    def _test_conexion(self):
        if not self.authenticator:
            messagebox.showwarning("Atencion", "Authenticator no inicializado")
            return

        def task():
            ok, msg = self.authenticator.test_connection()
            self.after(0, lambda: (
                messagebox.showinfo("Test de Conexion", msg) if ok
                else messagebox.showerror("Test de Conexion", msg)
            ))

        Thread(target=task, daemon=True).start()

    def _backup_db(self):
        import shutil
        try:
            db_path = self.settings.get_db_path()
            backup_dir = Path(self.settings.data_dir) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{timestamp}.db"
            shutil.copy2(db_path, backup_path)
            import hashlib
            with open(backup_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            messagebox.showinfo(
                "Backup",
                f"Backup creado:\n{backup_path}\n\nSHA256: {checksum[:16]}..."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error creando backup: {e}")

    def _configurar_firebase(self):
        dialog = ctk.CTkInputDialog(
            text="Ingrese API Key de Firebase:",
            title="Configurar Firebase",
        )
        api_key = dialog.get_input()
        if api_key:
            dialog2 = ctk.CTkInputDialog(
                text="Ingrese Project ID de Firebase:",
                title="Configurar Firebase",
            )
            project_id = dialog2.get_input()
            if project_id:
                firebase_sync.configure(api_key, project_id)
                messagebox.showinfo("Firebase", "Firebase configurado correctamente")

    def _limpiar_cache(self):
        from database.repositories import TokenRepository
        session = self.session_factory()
        try:
            repo = TokenRepository(session)
            repo.clean_expired()
            session.commit()
            messagebox.showinfo("Cache", "Cache limpiado correctamente")
        except Exception as e:
            session.rollback()
            messagebox.showerror("Error", f"Error limpiando cache: {e}")
        finally:
            session.close()

    def _importar_clientes(self):
        filepath = filedialog.askopenfilename(
            title="Importar Clientes desde CSV",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
        )
        if filepath:
            from database.repositories import ContribuyenteRepository
            session = self.session_factory()
            try:
                repo = ContribuyenteRepository(session)
                import csv
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        repo.create({
                            "cuit": row.get("cuit", "").replace("-", ""),
                            "razon_social": row.get("razon_social", row.get("nombre", "")),
                            "condicion_iva": int(row.get("condicion_iva", 5)),
                            "domicilio": row.get("domicilio", ""),
                            "telefono": row.get("telefono", ""),
                            "email": row.get("email", ""),
                        })
                        count += 1
                session.commit()
                messagebox.showinfo("Importacion", f"{count} clientes importados")
            except Exception as e:
                session.rollback()
                messagebox.showerror("Error", f"Error importando: {e}")
            finally:
                session.close()

    def _importar_productos(self):
        filepath = filedialog.askopenfilename(
            title="Importar Productos desde CSV",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
        )
        if filepath:
            from database.repositories import ProductoRepository
            session = self.session_factory()
            try:
                repo = ProductoRepository(session)
                import csv
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        repo.create({
                            "codigo": row.get("codigo", f"IMP-{count}"),
                            "descripcion": row.get("descripcion", ""),
                            "tipo": row.get("tipo", "PRODUCTO"),
                            "precio_base": float(row.get("precio_base", 0)),
                            "alicuota_iva": float(row.get("alicuota_iva", 21)),
                        })
                        count += 1
                session.commit()
                messagebox.showinfo("Importacion", f"{count} productos importados")
            except Exception as e:
                session.rollback()
                messagebox.showerror("Error", f"Error importando: {e}")
            finally:
                session.close()

    def _acerca_de(self):
        messagebox.showinfo(
            "Acerca de ARCA Facturador",
            f"{self.APP_NAME} v{self.VERSION}\n\n"
            "Sistema de Facturacion Electronica\n"
            "Integracion con ARCA (ex AFIP)\n\n"
            "Desarrollado en Python con CustomTkinter\n"
            "(c) 2026 - Todos los derechos reservados",
        )

    def _abrir_manual(self):
        manual_path = Path("docs/manual_usuario.pdf")
        if manual_path.exists():
            os.startfile(str(manual_path))
        else:
            messagebox.showinfo("Manual", "Manual de usuario no disponible")

    def _show_notification(self, title: str, message: str, level: str = "info"):
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name=self.APP_NAME,
                timeout=10,
            )
        except Exception:
            self.logger.warning(f"Notificacion: {title} - {message}")

    def _on_close(self):
        if messagebox.askokcancel("Salir", "Desea salir de ARCA Facturador?"):
            try:
                if self.session_factory:
                    self.session_factory.close_all()
            except Exception:
                pass
            self.destroy()
            sys.exit(0)


class PanelDashboard(ctk.CTkFrame):
    def __init__(self, parent, settings, session_factory, facturador):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings
        self.session_factory = session_factory
        self.facturador = facturador
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Panel de Control",
                      font=FONT_HEADING,
                      text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=4, pady=(0, 16))

        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def create_kpi(parent, title, value, gradient_color):
            card = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=12,
                                 border_width=1, border_color=COLOR_CARD_BORDER)
            card.grid(row=0, column=0, padx=4, sticky="nsew")
            card.grid_propagate(False)
            card.configure(height=100)
            ctk.CTkLabel(card, text=title, font=FONT_SMALL,
                          text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=14, pady=(14, 0))
            ctk.CTkLabel(card, text=value, font=(FONT_FAMILY, 22, "bold"),
                          text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(4, 14))

        self.kpi_facturas = ctk.CTkLabel(kpi_frame, text="0", font=(FONT_FAMILY, 22, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.kpi_total = ctk.CTkLabel(kpi_frame, text="$ 0,00", font=(FONT_FAMILY, 22, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.kpi_pendientes = ctk.CTkLabel(kpi_frame, text="0", font=(FONT_FAMILY, 22, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.kpi_dias = ctk.CTkLabel(kpi_frame, text="--", font=(FONT_FAMILY, 22, "bold"), text_color=COLOR_TEXT_PRIMARY)

        cards_data = [
            (COLOR_GRADIENT_A, "Facturas Emitidas", self.kpi_facturas),
            (COLOR_GRADIENT_B, "Total Facturado", self.kpi_total),
            (COLOR_ORANGE, "Pendientes", self.kpi_pendientes),
            (COLOR_RED, "Certificado", self.kpi_dias),
        ]
        for col, (color, title, label) in enumerate(cards_data):
            card = ctk.CTkFrame(kpi_frame, fg_color="transparent", corner_radius=12,
                                 border_width=1, border_color=COLOR_CARD_BORDER)
            card.grid(row=0, column=col, padx=4, sticky="nsew")
            card.grid_propagate(False)
            card.configure(height=100)
            ctk.CTkLabel(card, text=title, font=FONT_SMALL,
                          text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=14, pady=(14, 0))
            label.pack(anchor="w", padx=14, pady=(4, 14))

        self._cargar_kpis()

    def _cargar_kpis(self):
        def task():
            try:
                from database.repositories import FacturaRepository
                from core.auth import Authenticator
                session = self.session_factory()
                try:
                    repo = FacturaRepository(session)
                    from datetime import date, timedelta
                    stats = repo.get_estadisticas(date.today() - timedelta(days=30), date.today())
                    pendientes = len(repo.get_pendientes())
                    kpis = {
                        "facturas": stats.get("cantidad_facturas", 0),
                        "total": stats.get("total_facturado", 0),
                        "pendientes": pendientes,
                    }
                    try:
                        auth = Authenticator(self.settings)
                        info = auth.get_cert_info()
                        kpis["dias"] = info.get("days_remaining", 0)
                    except Exception:
                        kpis["dias"] = "N/A"
                finally:
                    session.close()
                self.after(0, lambda: self._actualizar_kpis(kpis))
            except Exception as e:
                self.after(0, lambda: None)

        Thread(target=task, daemon=True).start()

    def _actualizar_kpis(self, kpis):
        from utils.formatters import Formatters
        self.kpi_facturas.configure(text=str(kpis.get("facturas", 0)))
        self.kpi_total.configure(text=Formatters.formatear_importe(kpis.get("total", 0)))
        self.kpi_pendientes.configure(text=str(kpis.get("pendientes", 0)))
        dias = kpis.get("dias", "N/A")
        color = COLOR_TEXT_PRIMARY
        if isinstance(dias, int):
            if dias <= 7:
                color = COLOR_RED
            elif dias <= 30:
                color = COLOR_ORANGE
        self.kpi_dias.configure(text=str(dias) if isinstance(dias, int) else "N/A",
                                 text_color=color)

    def on_activate(self):
        self._cargar_kpis()


def main():
    try:
        settings = ConfigManager.load()
        app = ARCAFacturadorApp(settings)
        app.mainloop()
    except Exception as e:
        messagebox.showerror(
            "Error Fatal",
            f"Error al iniciar la aplicacion:\n{e}\n\n"
            "Verifique la configuracion e intente nuevamente.",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
