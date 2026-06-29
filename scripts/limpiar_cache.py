#!/usr/bin/env python3
"""
Script para limpiar cache, tokens expirados y archivos temporales.
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import get_session_factory
from database.repositories import TokenRepository
from config import ConfigManager
from loguru import logger


class CacheCleaner:
    def __init__(self):
        settings = ConfigManager.get_settings()
        self.temp_dir = Path(settings.temp_dir)
        self.log_dir = Path(settings.log_dir)
        self.db_path = settings.get_db_path()
        self.session_factory = get_session_factory(str(self.db_path))

    def limpiar_tokens_expirados(self) -> int:
        session = self.session_factory()
        try:
            repo = TokenRepository(session)
            count = repo.clean_expired()
            session.commit()
            logger.info(f"Tokens expirados eliminados: {count}")
            return count
        finally:
            session.close()

    def limpiar_archivos_temporales(self, max_dias: int = 7) -> int:
        count = 0
        if self.temp_dir.exists():
            for f in self.temp_dir.glob("*"):
                if f.is_file():
                    edad = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
                    if edad > timedelta(days=max_dias):
                        f.unlink()
                        count += 1
                elif f.is_dir():
                    shutil.rmtree(f)
                    count += 1
            logger.info(f"Archivos temporales eliminados: {count}")
        return count

    def limpiar_logs_viejos(self, max_dias: int = 90) -> int:
        count = 0
        if self.log_dir.exists():
            for f in self.log_dir.glob("*.log*"):
                if f.is_file():
                    edad = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
                    if edad > timedelta(days=max_dias):
                        f.unlink()
                        count += 1
            logger.info(f"Logs viejos eliminados: {count}")
        return count

    def limpiar_pendientes_antiguos(self, max_dias: int = 30) -> int:
        from database.models import Factura, EstadoFactura
        session = self.session_factory()
        try:
            desde = datetime.now() - timedelta(days=max_dias)
            pendientes = session.query(Factura).filter(
                Factura.estado == EstadoFactura.PENDIENTE.value,
                Factura.fecha_emision < desde,
            ).all()
            count = len(pendientes)
            for p in pendientes:
                p.estado = "ERROR"
                p.error_message = "Eliminado por antiguedad"
            session.commit()
            logger.info(f"Pendientes antiguos marcados como error: {count}")
            return count
        finally:
            session.close()

    def limpiar_todo(self):
        t1 = self.limpiar_tokens_expirados()
        t2 = self.limpiar_archivos_temporales()
        t3 = self.limpiar_logs_viejos()
        t4 = self.limpiar_pendientes_antiguos()
        return t1 + t2 + t3 + t4


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Limpiar cache de ARCA Facturador")
    parser.add_argument("--todo", action="store_true", help="Limpiar todo")
    parser.add_argument("--tokens", action="store_true", help="Limpiar tokens expirados")
    parser.add_argument("--temp", action="store_true", help="Limpiar archivos temporales")
    parser.add_argument("--logs", action="store_true", help="Limpiar logs viejos")
    parser.add_argument("--pendientes", action="store_true", help="Limpiar pendientes antiguos")

    args = parser.parse_args()
    cleaner = CacheCleaner()

    if args.todo or not any([args.tokens, args.temp, args.logs, args.pendientes]):
        total = cleaner.limpiar_todo()
        print(f"Cache limpiado: {total} elementos eliminados")
    else:
        if args.tokens:
            print(f"Tokens eliminados: {cleaner.limpiar_tokens_expirados()}")
        if args.temp:
            print(f"Temp eliminados: {cleaner.limpiar_archivos_temporales()}")
        if args.logs:
            print(f"Logs eliminados: {cleaner.limpiar_logs_viejos()}")
        if args.pendientes:
            print(f"Pendientes: {cleaner.limpiar_pendientes_antiguos()}")


if __name__ == "__main__":
    main()
