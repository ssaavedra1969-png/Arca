import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger


class FirebaseSync:
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None):
        self.api_key = api_key
        self.project_id = project_id
        self.base_url = f"https://{project_id}.firebaseio.com" if project_id else None
        self._enabled = bool(api_key and project_id)
        self._cache: Dict[str, Any] = {}
        self._last_sync: Dict[str, datetime] = {}

    def configure(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        self.base_url = f"https://{project_id}.firebaseio.com"
        self._enabled = True
        logger.info("Firebase sync configured")

    def is_enabled(self) -> bool:
        return self._enabled

    def sync_factura(self, factura_data: Dict[str, Any]) -> bool:
        if not self._enabled:
            logger.warning("Firebase sync not configured")
            return False
        try:
            import httpx
            factura_id = factura_data.get("uuid", factura_data.get("id", str(time.time())))
            url = f"{self.base_url}/facturas/{factura_id}.json"
            response = httpx.put(url, json=factura_data, timeout=10)
            if response.is_success:
                logger.info(f"Factura {factura_id} synced to Firebase")
                self._last_sync["facturas"] = datetime.now()
                return True
            logger.error(f"Firebase sync failed: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            logger.error(f"Firebase sync error: {e}")
            return False

    def sync_config(self, config_data: Dict[str, Any]) -> bool:
        if not self._enabled:
            return False
        try:
            import httpx
            url = f"{self.base_url}/config.json"
            response = httpx.put(url, json=config_data, timeout=10)
            return response.is_success
        except Exception as e:
            logger.error(f"Firebase config sync error: {e}")
            return False

    def get_facturas_pendientes(self) -> List[Dict[str, Any]]:
        if not self._enabled:
            return []
        try:
            import httpx
            url = f"{self.base_url}/facturas_pendientes.json"
            response = httpx.get(url, timeout=10)
            if response.is_success and response.json():
                data = response.json()
                return list(data.values()) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.error(f"Firebase read error: {e}")
            return []

    def backup_database(self, db_path: Path) -> bool:
        if not self._enabled:
            return False
        try:
            import httpx
            with open(db_path, "rb") as f:
                db_content = f.read()
            import base64
            encoded = base64.b64encode(db_content).decode()
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "content": encoded,
                "filename": db_path.name,
            }
            url = f"{self.base_url}/backups/{db_path.stem}_{int(time.time())}.json"
            response = httpx.put(url, json=backup_data, timeout=30)
            return response.is_success
        except Exception as e:
            logger.error(f"Firebase backup error: {e}")
            return False

    def get_remote_config(self) -> Optional[Dict[str, Any]]:
        if not self._enabled:
            return None
        try:
            import httpx
            url = f"{self.base_url}/config.json"
            response = httpx.get(url, timeout=10)
            if response.is_success:
                return response.json()
            return None
        except Exception:
            return None


firebase_sync = FirebaseSync()
