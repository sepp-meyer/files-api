import hmac, hashlib, time
import datetime as dt
from functools import wraps
from flask import request, abort

from config import Config
from models import ApiToken, db

def sha256_of_file(path, chunk_size=1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def sign_download(file_id: str, exp_ts: int) -> str:
    msg = f"{file_id}:{exp_ts}".encode()
    return hmac.new(Config.DOWNLOAD_HMAC_SECRET.encode(), msg, hashlib.sha256).hexdigest()

def verify_signature(file_id: str, exp_ts: int, sig: str) -> bool:
    if exp_ts < int(time.time()):
        return False
    expected = sign_download(file_id, exp_ts)
    return hmac.compare_digest(expected, sig)

def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def require_token(scopes_required=("read",)):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            token = request.args.get("token") or request.headers.get("Authorization", "").replace("Bearer ","")
            if not token:
                abort(401, "Token fehlt")
            rec = ApiToken.query.filter_by(token_hash=hash_token(token)).first()
            now = dt.datetime.utcnow()
            if (not rec) or rec.revoked or (rec.expires_at and rec.expires_at < now):
                abort(403, "Token ungültig oder abgelaufen")
            token_scopes = {s.strip() for s in (rec.scopes or "").split(",") if s.strip()}
            if not set(scopes_required).issubset(token_scopes):
                abort(403, "Token hat nicht die benötigten Scopes")
            rec.last_used_at = now
            db.session.commit()
            return fn(*args, **kwargs)
        return wrapped
    return deco
