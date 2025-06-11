from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    """Base config"""
    SECRET_KEY = os.getenv("SECRET_KEY")
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_TRANSLATION_DIRECTORIES = './translations'

    """Service config"""
    DB_PATH = os.getenv("DB_PATH")