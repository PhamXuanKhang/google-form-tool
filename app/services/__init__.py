from config import Config
from app.services.storage_service import StorageService

def get_storage_service():
    return StorageService(Config.DB_PATH)