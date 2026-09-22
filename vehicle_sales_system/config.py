import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'autovault-local-demo-only')
    BRAND = 'AutoVault'
    DEMO_MODE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 1024 * 1024
