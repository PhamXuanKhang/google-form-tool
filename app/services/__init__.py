from config import Config
from tinydb import TinyDB, Query

def get_storage_service():
    return StorageService(Config.DB_PATH)
