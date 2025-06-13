from config import Config
from app.services.storage_service import StorageService

storage_service = StorageService(Config.DB_PATH)