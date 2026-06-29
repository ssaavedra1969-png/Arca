#!/usr/bin/env python3
"""
Script de backup automatico de la base de datos.
Crea backups comprimidos con timestamp y verifica integridad.
"""
import sys
import os
import shutil
import hashlib
import gzip
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager
from loguru import logger


class DatabaseBackup:
    def __init__(self, db_path: Optional[str] = None, backup_dir: Optional[str] = None):
        settings = ConfigManager.get_settings()
        self.db_path = Path(db_path or settings.get_db_path())
        self.backup_dir = Path(backup_dir or settings.data_dir) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 30

    def crear_backup(self, comprimir: bool = True) -> Path:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Backup creado: {backup_path}")

        checksum = self._calcular_checksum(backup_path)
        checksum_file = backup_path.with_suffix(".sha256")
        checksum_file.write_text(checksum)
        logger.info(f"SHA256: {checksum}")

        if comrimir:
            gz_path = backup_path.with_suffix(".db.gz")
            with open(backup_path, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path.unlink()
            backup_path = gz_path
            logger.info(f"Backup comprimido: {gz_path}")

        self._limpiar_viejos()
        return backup_path

    def _calcular_checksum(self, filepath: Path) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def _limpiar_viejos(self):
        backups = sorted(self.backup_dir.glob("backup_*"))
        while len(backups) > self.max_backups:
            viejo = backups.pop(0)
            viejo.unlink()
            logger.info(f"Backup viejo eliminado: {viejo}")

    def restaurar(self, backup_path: Path) -> bool:
        if not backup_path.exists():
            logger.error(f"Backup no encontrado: {backup_path}")
            return False

        checksum_file = backup_path.with_suffix(".sha256")
        if checksum_file.exists():
            checksum_original = checksum_file.read_text().strip()
            checksum_actual = self._calcular_checksum(backup_path)
            if checksum_original != checksum_actual:
                logger.error("Checksum no coincide. Backup corrupto.")
                return False

        db_backup = self.db_path.with_suffix(".db.bak")
        if self.db_path.exists():
            shutil.copy2(self.db_path, db_backup)
            logger.info(f"Backup previo guardado: {db_backup}")

        shutil.copy2(backup_path, self.db_path)
        logger.info(f"Base de datos restaurada desde: {backup_path}")
        return True

    def listar_backups(self) -> list:
        backups = sorted(self.backup_dir.glob("backup_*"))
        result = []
        for b in backups:
            size = b.stat().st_size
            modified = datetime.fromtimestamp(b.stat().st_mtime)
            result.append({
                "path": str(b),
                "size": size,
                "size_human": self._human_size(size),
                "modified": modified,
            })
        return result

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backup de base de datos ARCA Facturador")
    parser.add_argument("accion", choices=["crear", "listar", "restaurar"],
                        help="Accion a realizar")
    parser.add_argument("--archivo", help="Archivo de backup para restaurar")
    parser.add_argument("--db", help="Ruta a la base de datos")

    args = parser.parse_args()
    backup = DatabaseBackup(db_path=args.db)

    if args.accion == "crear":
        path = backup.crear_backup()
        print(f"Backup creado: {path}")
    elif args.accion == "listar":
        backups = backup.listar_backups()
        if not backups:
            print("No hay backups disponibles")
        else:
            print(f"{'Archivo':<50} {'Tamaño':<10} {'Fecha':<20}")
            print("-" * 80)
            for b in backups:
                print(f"{b['path']:<50} {b['size_human']:<10} {b['modified'].strftime('%d/%m/%Y %H:%M'):<20}")
    elif args.accion == "restaurar":
        if not args.archivo:
            print("Debe especificar --archivo con la ruta del backup")
            return
        ok = backup.restaurar(Path(args.archivo))
        print("Restauracion exitosa" if ok else "Error en restauracion")


if __name__ == "__main__":
    main()
