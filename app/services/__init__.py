from config import Config
from tinydb import TinyDB, Query

def create_db():
    """
    """
    db = TinyDB(Config.DBPATH)
    return db