from pathlib import Path
from config import Config
from app.services.storage_service import StorageService


def get_storage_service():
    db_path = Config.DB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return StorageService(db_path)
