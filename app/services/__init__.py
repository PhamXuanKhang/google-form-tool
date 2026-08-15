from pathlib import Path
from config import Config
from app.services.storage_service import StorageService

# Overridable factory. Tests install a stub so route code can be exercised
# without touching the on-disk TinyDB. Threads use this too, so it must not
# depend on a Flask application context.
_storage_provider = None


def set_storage_provider(provider):
    """Install a storage factory. Pass None to restore the default."""
    global _storage_provider
    _storage_provider = provider


def get_storage_service():
    if _storage_provider is not None:
        return _storage_provider()
    db_path = Config.DB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return StorageService(db_path)
