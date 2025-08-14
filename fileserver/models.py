import datetime as dt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.String(36), primary_key=True)  # UUID str
    title = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(128), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    orig_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(1024), nullable=False)
    checksum_sha256 = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

class ApiToken(db.Model):
    __tablename__ = "api_tokens"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)  # SHA-256
    scopes = db.Column(db.String(255), default="read")  # "read,sign"
    revoked = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
