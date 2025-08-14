import uuid, mimetypes, secrets
import datetime as dt
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, abort, jsonify  # request ist wichtig

from . import admin_bp
from ..config import Config
from ..models import db, File, ApiToken
from ..utils import sha256_of_file, sign_download, hash_token

@admin_bp.get("/")
def index():
    files = File.query.order_by(File.created_at.desc()).all()
    return render_template("admin/index.html", files=files)

@admin_bp.post("/upload")
def upload():
    title = request.form.get("title","").strip()
    year = request.form.get("year", type=int)
    file = request.files.get("file")
    if not file or not title:
        abort(400, "Titel und Datei erforderlich")
    filename = secure_filename(file.filename or "")
    if not filename or ('.' not in filename):
        abort(400, "Ungültiger Dateiname")
    ext = filename.rsplit(".",1)[-1].lower()
    if ext not in Config.ALLOWED_EXT:
        abort(400, "Dateityp nicht erlaubt")

    fid = str(uuid.uuid4())
    target_dir = Config.STORAGE_DIR / fid
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / f"original.{ext}"
    file.save(dest)

    size = dest.stat().st_size
    mime = mimetypes.guess_type(dest.name)[0] or "application/octet-stream"
    checksum = sha256_of_file(dest)

    rec = File(
        id=fid, title=title, year=year, mime_type=mime, size_bytes=size,
        orig_filename=filename, storage_path=str(dest), checksum_sha256=checksum
    )
    db.session.add(rec)
    db.session.commit()
    return redirect(url_for("admin.index"))

@admin_bp.get("/admin/sign/<file_id>")
def admin_sign(file_id):
    File.query.get_or_404(file_id)  # existiert?
    exp = int(dt.datetime.utcnow().timestamp()) + 3600
    sig = sign_download(file_id, exp)
    dl_url = url_for("api.api_file_download", file_id=file_id, _external=True)
    return jsonify({"download_url": f"{dl_url}?exp={exp}&sig={sig}", "valid_until_utc": dt.datetime.utcfromtimestamp(exp).isoformat() + "Z"})

# -------- Token Verwaltung ----------

@admin_bp.get("/admin/tokens")
def admin_tokens():
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    return render_template("admin/tokens.html", tokens=tokens)

@admin_bp.post("/admin/tokens")
def admin_token_create():
    name = request.form.get("name","").strip()
    if not name:
        abort(400, "Name erforderlich")
    days = request.form.get("days", type=int)
    scopes = request.form.get("scopes","read").strip() or "read"
    raw = secrets.token_urlsafe(32)
    expires = (dt.datetime.utcnow() + dt.timedelta(days=days)) if days else None
    rec = ApiToken(name=name, token_hash=hash_token(raw), scopes=scopes, expires_at=expires)
    db.session.add(rec); db.session.commit()
    return jsonify({"token": raw, "note": "Bitte sicher speichern. Der Token wird nicht erneut angezeigt."})

@admin_bp.post("/admin/tokens/<int:token_id>/revoke")
def admin_token_revoke(token_id):
    t = ApiToken.query.get_or_404(token_id)
    t.revoked = True
    db.session.commit()
    return redirect(url_for("admin.admin_tokens"))

# -------- Embed-Generator pro Datei ----------

@admin_bp.get("/admin/embed/<file_id>")
def admin_embed(file_id):
    f = File.query.get_or_404(file_id)
    base_url = request.url_root.rstrip("/")  # z.B. http://127.0.0.1:5000
    kind = "audio" if (f.mime_type or "").startswith("audio") else ("video" if (f.mime_type or "").startswith("video") else "audio")
    return render_template("admin/embed.html", file=f, base_url=base_url, kind=kind)
