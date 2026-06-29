import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from config import ConfigManager


class AuditLogHandler:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._setup_db()

    def _setup_db(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT,
                function TEXT,
                user TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                session_id TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
        """)
        conn.commit()
        conn.close()

    def write(self, record):
        import sqlite3
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """INSERT INTO audit_log (timestamp, level, module, function, user, action, details, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record["time"].strftime("%Y-%m-%d %H:%M:%S"),
                    record["level"].name,
                    record.get("module", ""),
                    record.get("function", ""),
                    record.get("extra", {}).get("user", "system"),
                    record.get("message", ""),
                    json.dumps(record.get("extra", {})),
                    record.get("extra", {}).get("session_id", ""),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


class LoggerManager:
    _initialized = False

    @classmethod
    def setup(cls, settings=None):
        if cls._initialized:
            return logger

        if settings is None:
            settings = ConfigManager.get_settings()

        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_level = settings.log_level.upper()
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        logger.remove()

        logger.add(
            sys.stderr,
            format=log_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

        logger.add(
            log_dir / "arca_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation=settings.log_rotation_bytes,
            retention=settings.log_retention_days,
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )

        logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message} | {exception}",
            level="ERROR",
            rotation=settings.log_rotation_bytes,
            retention=settings.log_retention_days * 2,
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )

        if settings.audit_enabled:
            audit_handler = AuditLogHandler(settings.get_db_path())
            logger.add(
                audit_handler.write,
                format="{message}",
                level="INFO",
                filter=lambda record: record["extra"].get("audit", False),
            )

        cls._initialized = True
        logger.info("Logger inicializado correctamente")
        return logger

    @classmethod
    def get_logger(cls):
        if not cls._initialized:
            cls.setup()
        return logger


log = LoggerManager.get_logger
