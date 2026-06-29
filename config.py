import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    app_name: str = "ARCA Facturador"
    app_version: str = "1.0.0"
    app_debug: bool = False
    app_theme: str = "dark"

    db_path: str = "data/arca_facturador.db"
    db_wal_mode: bool = True
    db_backup_enabled: bool = True
    db_backup_interval_hours: int = 24

    arca_homo: bool = False
    arca_cuit: int = 20345678901
    arca_punto_venta: int = 1
    arca_cert_file: str = "certs/certificado.crt"
    arca_key_file: str = "certs/clave.key"
    arca_cert_pin: str = ""
    arca_wsaa_url: str = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
    arca_wsfe_url: str = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
    arca_homo_wsaa_url: str = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
    arca_homo_wsfe_url: str = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx"
    arca_timeout_connect: int = 30
    arca_timeout_read: int = 60
    arca_retry_max_attempts: int = 3
    arca_retry_base_delay: float = 2.0
    arca_retry_max_delay: float = 30.0
    arca_token_cache_minutes: int = 390

    encryption_salt: str = "arcafacturador2024_salt"
    encryption_algorithm: str = "aes-256-gcm"
    log_level: str = "INFO"
    log_retention_days: int = 30
    log_rotation_bytes: int = 10485760
    log_dir: str = "logs"
    audit_enabled: bool = True
    session_timeout_minutes: int = 60

    report_logo: str = "resources/logo.png"
    report_footer: str = "Gracias por su compra"
    report_papel: str = "A4"
    report_copias: int = 1
    report_qr_size: int = 100

    internal_api_enabled: bool = False
    internal_api_host: str = "127.0.0.1"
    internal_api_port: int = 8742

    update_check_interval: int = 86400
    update_repo_url: str = "https://api.github.com/repos/user/arca-facturador/releases/latest"
    update_auto_download: bool = False
    update_channel: str = "stable"

    notif_cert_aviso_dias: int = 7
    notif_sincronizacion_intervalo_minutos: int = 30
    notif_sonido: bool = True

    moneda_defecto: str = "ARS"
    moneda_cotizacion_api: str = "https://api-dolar-argentina.herokuapp.com/api/dolaroficial"
    moneda_cotizacion_automatica: bool = True
    moneda_actualizacion_horas: int = 6

    cert_dir: str = "certs"
    data_dir: str = "data"
    temp_dir: str = "temp"
    resources_dir: str = "resources"
    templates_dir: str = "templates"

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False

    @validator("arca_cuit")
    def validar_cuit(cls, v):
        if v and not (20000000000 <= v <= 30999999999):
            raise ValueError(f"CUIT invalido: {v}")
        return v

    def get_wsaa_url(self) -> str:
        return self.arca_homo_wsaa_url if self.arca_homo else self.arca_wsaa_url

    def get_wsfe_url(self) -> str:
        return self.arca_homo_wsfe_url if self.arca_homo else self.arca_wsfe_url

    def get_cert_path(self) -> Path:
        p = Path(self.arca_cert_file)
        return p if p.is_absolute() else Path.cwd() / self.arca_cert_file

    def get_key_path(self) -> Path:
        p = Path(self.arca_key_file)
        return p if p.is_absolute() else Path.cwd() / self.arca_key_file

    def get_db_path(self) -> Path:
        p = Path(self.db_path)
        return p if p.is_absolute() else Path.cwd() / self.db_path


class ConfigManager:
    _instance = None
    _settings: Optional[Settings] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> Settings:
        if cls._settings is not None:
            return cls._settings

        env_path = Path(".env")
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)

        settings = Settings()

        if config_file:
            cfg_path = Path(config_file)
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                if yaml_config:
                    settings = cls._merge_yaml(settings, yaml_config)

        cls._settings = settings
        return settings

    @staticmethod
    def _merge_yaml(settings: Settings, yaml_config: Dict[str, Any]) -> Settings:
        flat = {}
        for section, values in yaml_config.items():
            if isinstance(values, dict):
                for key, val in values.items():
                    env_key = f"{section}_{key}"
                    flat[env_key] = val
            else:
                flat[section] = values

        for field_name in settings.model_fields_set:
            env_name = field_name.lower()
            if env_name in flat:
                setattr(settings, field_name, flat[env_name])

        return settings

    @classmethod
    def get_settings(cls) -> Settings:
        if cls._settings is None:
            cls.load()
        return cls._settings


config_manager = ConfigManager()
