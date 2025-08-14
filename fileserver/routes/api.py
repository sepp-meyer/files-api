import time, datetime as dt
from pathlib import Path
from flask import jsonify, url_for, abort, send_file, make_response, redirect, request

from . import api_bp
from models import File
from utils import require_token, sign_download, verify_signature

@api_bp.get("/files")
@require_token(scopes_required=("read",))
def api_list():
    items = File.query.order_by(File.created_at.desc()).limit(100).all()
    return jsonify([{
        "id": f.id,
        "title": f.title,
        "year": f.year,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "created_at": f.created_at.isoformat() + "Z"
    } for f in items])

@api_bp.get("/files/<file_id>")
@require_token(scopes_required=("read",))
def api_file_meta(file_id):
    f = File.query.get_or_404(file_id)
    return jsonify({
        "id": f.id,
        "title": f.title,
        "year": f.year,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "orig_filename": f.orig_filename,
        "checksum_sha256": f.checksum_sha256,
        "created_at": f.created_at.isoformat() + "Z"
    })

@api_bp.get("/files/<file_id>/signed-url")
@require_token(scopes_required=("read",))
def api_signed_url(file_id):
    _ = File.query.get_or_404(file_id)
    exp = int(time.time()) + 900  # 15 Minuten
    sig = sign_download(file_id, exp)
    dl_url = url_for("api.api_file_download", file_id=file_id, _external=True)
    return jsonify({"download_url": f"{dl_url}?exp={exp}&sig={sig}", "exp": exp})

@api_bp.get("/embed/<file_id>")
@require_token(scopes_required=("read",))
def api_embed(file_id):
    exp = int(time.time()) + 300
    sig = sign_download(file_id, exp)
    dl_url = url_for("api.api_file_download", file_id=file_id, _external=True)
    resp = redirect(f"{dl_url}?exp={exp}&sig={sig}", code=302)
    resp.headers["Cache-Control"] = "private, max-age=60"
    return resp

@api_bp.get("/files/<file_id>/download")
def api_file_download(file_id):
    exp = request.args.get("exp", type=int)
    sig = request.args.get("sig", default="")
    if not exp or not sig or not verify_signature(file_id, exp, sig):
        abort(403, "Ungültige oder abgelaufene Signatur")

    f = File.query.get_or_404(file_id)
    path = Path(f.storage_path)
    if not path.exists():
        abort(404)

    resp = make_response(send_file(
        path,
        mimetype=f.mime_type,
        as_attachment=False,
        conditional=True,
        etag=True,
        last_modified=dt.datetime.utcfromtimestamp(path.stat().st_mtime)
    ))
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Cache-Control"] = "public, max-age=86400"
    resp.headers["Content-Disposition"] = f'inline; filename="{f.orig_filename}"'
    return resp
