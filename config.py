import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'autovault-local-demo-only')
    BRAND = 'AutoVault'
    DEMO_MODE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_PHOTO_BYTES = 5 * 1024 * 1024
    # Allow multipart overhead; the photo service enforces the file's 5 MB limit.
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
