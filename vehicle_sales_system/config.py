import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    BRAND = 'IGNITE'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    MAX_PHOTO_BYTES = 5 * 1024 * 1024
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
