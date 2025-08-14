import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR/'app.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_HMAC_SECRET = os.getenv("DOWNLOAD_HMAC_SECRET", "download-secret-change-me")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
    ALLOWED_EXT = {"mp3", "mp4", "wav", "flac", "jpg", "png", "pdf"}

def get_cors_resources():
    # In DEV erlauben wir alle Origins, sonst Liste
    if not Config.CORS_ORIGINS:
        return {r"/api/*": {"origins": "*"}}
    origins = [o.strip() for o in Config.CORS_ORIGINS.split(",") if o.strip()]
    return {r"/api/*": {"origins": origins}}
