# fileserver/routes/admin.py
import uuid
import mimetypes
import secrets
import shutil
import datetime as dt
from pathlib import Path

from werkzeug.utils import secure_filename
from flask import (
    render_template, request, redirect, url_for, abort, jsonify,
    send_file, make_response
)

from . import admin_bp
from ..config import Config
from ..models import db, File, ApiToken
from ..utils import sha256_of_file, hash_token


# ---------- Dashboard / Liste ----------

@admin_bp.get("/")
def index():
    files = File.query.order_by(File.created_at.desc()).all()
    return render_template("admin/index.html", files=files)


# ---------- Upload ----------

@admin_bp.post("/upload")
def upload():
    title = request.form.get("title", "").strip()
    year = request.form.get("year", type=int)
    file = request.files.get("file")

    if not file or not title:
        abort(400, "Titel und Datei erforderlich")
    filename = secure_filename(file.filename or "")
    if not filename or "." not in filename:
        abort(400, "Ungültiger Dateiname")

    ext = filename.rsplit(".", 1)[-1].lower()
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
        id=fid,
        title=title,
        year=year,
        mime_type=mime,
        size_bytes=size,
        orig_filename=filename,
        storage_path=str(dest),
        checksum_sha256=checksum,
    )
    db.session.add(rec)
    db.session.commit()
    return redirect(url_for("admin.index"))


# ---------- Token-Verwaltung ----------

@admin_bp.get("/tokens")
def admin_tokens():
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    return render_template("admin/tokens.html", tokens=tokens)

@admin_bp.post("/tokens")
def admin_token_create():
    name = request.form.get("name", "").strip()
    if not name:
        abort(400, "Name erforderlich")

    days = request.form.get("days", type=int)
    scopes = request.form.get("scopes", "read").strip() or "read"

    raw = secrets.token_urlsafe(32)
    expires = (dt.datetime.utcnow() + dt.timedelta(days=days)) if days else None

    rec = ApiToken(
        name=name,
        token_hash=hash_token(raw),
        scopes=scopes,
        expires_at=expires
    )
    db.session.add(rec)
    db.session.commit()

    return jsonify({
        "token": raw,
        "note": "Bitte sicher speichern. Der Token wird nicht erneut angezeigt."
    })

@admin_bp.post("/tokens/<int:token_id>/revoke")
def admin_token_revoke(token_id):
    t = ApiToken.query.get_or_404(token_id)
    t.revoked = True
    db.session.commit()
    return redirect(url_for("admin.admin_tokens"))

@admin_bp.post("/tokens/<int:token_id>/delete")
def admin_token_delete(token_id):
    t = ApiToken.query.get_or_404(token_id)
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("admin.admin_tokens"))


# ---------- Datei-Detail / Edit / Delete ----------

@admin_bp.get("/files/<file_id>")
def file_detail(file_id):
    f = File.query.get_or_404(file_id)
    mt = (f.mime_type or "")
    if mt.startswith("video"):
        kind = "video"
    elif mt.startswith("audio"):
        kind = "audio"
    else:
        # Default: als Audio behandeln (für einfache Audios/Spoken Word)
        kind = "audio"
    return render_template("admin/file_detail.html", file=f, kind=kind)

@admin_bp.post("/files/<file_id>/update")
def file_update(file_id):
    f = File.query.get_or_404(file_id)
    title = request.form.get("title", "").strip()
    year = request.form.get("year", type=int)

    if not title:
        abort(400, "Titel erforderlich")
    f.title = title
    f.year = year
    db.session.commit()
    return redirect(url_for("admin.file_detail", file_id=file_id))

@admin_bp.post("/files/<file_id>/delete")
def file_delete(file_id):
    f = File.query.get_or_404(file_id)
    try:
        file_dir = Path(f.storage_path).parent
        if file_dir.is_dir() and file_dir != file_dir.anchor:
            shutil.rmtree(file_dir, ignore_errors=True)
    finally:
        db.session.delete(f)
        db.session.commit()
    return redirect(url_for("admin.index"))


# ---------- Admin-Stream (Preview ohne Token) ----------

@admin_bp.get("/stream/<file_id>")
def admin_stream(file_id):
    """
    Dient ausschließlich der Admin-Vorschau im Backend.
    Kein Token nötig – die App hat lokalen Zugriff.
    """
    f = File.query.get_or_404(file_id)
    path = Path(f.storage_path)
    if not path.is_file():
        abort(404)

    resp = make_response(send_file(
        str(path),
        mimetype=f.mime_type,
        as_attachment=False,
        conditional=True,  # ETag / If-Range / 206 Unterstützung durch Werkzeug
        etag=True,
        max_age=3600,
        last_modified=dt.datetime.utcfromtimestamp(path.stat().st_mtime)
    ))
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Cache-Control"] = "private, max-age=3600"
    resp.headers["Content-Disposition"] = f'inline; filename="{f.orig_filename}"'
    return resp
