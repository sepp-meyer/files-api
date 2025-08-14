import datetime as dt
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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

class AdminUser(db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

    @classmethod
    def create_or_update(cls, username: str, password: str):
        user = cls.query.filter_by(username=username).first()
        if not user:
            user = cls(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
        else:
            user.password_hash = generate_password_hash(password)
        db.session.commit()
        return user
