# app.py
import os, hmac, hashlib, mimetypes, time, uuid, datetime as dt
from pathlib import Path
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, abort, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from itsdangerous import TimestampSigner, BadSignature
from werkzeug.utils import secure_filename

# --- Config ---
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR/'app.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
DOWNLOAD_HMAC_SECRET = os.getenv("DOWNLOAD_HMAC_SECRET", "download-secret-change-me")

ALLOWED_EXT = {"mp3", "mp4", "wav", "flac", "jpg", "png", "pdf"}  # erweiterbar

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = SECRET_KEY
db = SQLAlchemy(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # feinjustieren in prod

# --- Model ---
class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.String(36), primary_key=True)  # UUID str
    title = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(128), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    orig_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(1024), nullable=False)  # absoluter Pfad
    checksum_sha256 = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()

# --- Hilfsfunktionen ---
def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXT

def sha256_of_file(path: Path, chunk_size=1024 * 1024):
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
    return hmac.new(DOWNLOAD_HMAC_SECRET.encode(), msg, hashlib.sha256).hexdigest()

def verify_signature(file_id: str, exp_ts: int, sig: str) -> bool:
    if exp_ts < int(time.time()):
        return False
    expected = sign_download(file_id, exp_ts)
    return hmac.compare_digest(expected, sig)

# --- Admin UI (minimal) ---
UPLOAD_HTML = """
<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8"><title>Fileserver Admin</title>
    <style>
      body{font-family:system-ui, sans-serif; max-width:900px; margin:2rem auto;}
      form, table{width:100%} input,button{padding:.5rem;margin:.2rem}
      .row{display:flex;gap:1rem;align-items:center}
    </style>
  </head>
  <body>
    <h1>Upload</h1>
    <form method="post" enctype="multipart/form-data" action="{{ url_for('admin_upload') }}">
      <div class="row">
        <input name="title" placeholder="Titel" required>
        <input name="year" placeholder="Erscheinungsjahr (optional)" type="number" min="0">
      </div>
      <input type="file" name="file" required>
      <button type="submit">Hochladen</button>
    </form>

    <h2>Dateien</h2>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr><th>UUID</th><th>Titel</th><th>Jahr</th><th>MIME</th><th>Größe</th><th>Aktionen</th></tr>
      {% for f in files %}
        <tr>
          <td><code>{{ f.id }}</code></td>
          <td>{{ f.title }}</td>
          <td>{{ f.year or '-' }}</td>
          <td>{{ f.mime_type }}</td>
          <td>{{ f.size_bytes }}</td>
          <td>
            <a href="{{ url_for('api_file_meta', file_id=f.id) }}" target="_blank">Meta</a> |
            <a href="{{ url_for('admin_sign', file_id=f.id) }}" target="_blank">Signierte URL</a>
          </td>
        </tr>
      {% endfor %}
    </table>
  </body>
</html>
"""

@app.get("/")
def admin_index():
    files = File.query.order_by(File.created_at.desc()).all()
    return render_template_string(UPLOAD_HTML, files=files)

@app.post("/upload")
def admin_upload():
    title = request.form.get("title", "").strip()
    year = request.form.get("year", type=int)
    file = request.files.get("file")
    if not file or not title:
        abort(400, "Titel und Datei erforderlich")
    if not allowed_file(file.filename):
        abort(400, "Dateityp nicht erlaubt")
    # UUID & Speicherpfad
    fid = str(uuid.uuid4())
    safe_name = secure_filename(file.filename)
    ext = os.path.splitext(safe_name)[1].lower()
    target_dir = STORAGE_DIR / fid
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / f"original{ext}"
    file.save(dest)

    size = dest.stat().st_size
    mime = mimetypes.guess_type(dest.name)[0] or "application/octet-stream"
    checksum = sha256_of_file(dest)

    rec = File(
        id=fid, title=title, year=year, mime_type=mime, size_bytes=size,
        orig_filename=safe_name, storage_path=str(dest), checksum_sha256=checksum
    )
    db.session.add(rec)
    db.session.commit()
    return redirect(url_for("admin_index"))

@app.get("/admin/sign/<file_id>")
def admin_sign(file_id):
    # signierte Download-URL (Standard 1 Stunde)
    exp = int(time.time()) + 3600
    sig = sign_download(file_id, exp)
    dl_url = url_for("api_file_download", file_id=file_id, _external=True)
    return jsonify({
        "download_url": f"{dl_url}?exp={exp}&sig={sig}",
        "valid_until_utc": dt.datetime.utcfromtimestamp(exp).isoformat() + "Z"
    })

# --- API ---
@app.get("/api/files")
def api_list():
    # einfache Liste (Pagination später)
    items = File.query.order_by(File.created_at.desc()).limit(100).all()
    return jsonify([{
        "id": f.id,
        "title": f.title,
        "year": f.year,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "created_at": f.created_at.isoformat() + "Z"
    } for f in items])

@app.get("/api/files/<file_id>")
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

@app.get("/api/files/<file_id>/download")
def api_file_download(file_id):
    # Signatur prüfen
    exp = request.args.get("exp", type=int)
    sig = request.args.get("sig", default="")
    if not exp or not sig or not verify_signature(file_id, exp, sig):
        abort(403, "Ungültige oder abgelaufene Signatur")

    f = File.query.get_or_404(file_id)
    path = Path(f.storage_path)
    if not path.exists():
        abort(404)

    # Effizientes Streaming mit Range-Unterstützung
    # send_file + conditional=True liefert ETag/Last-Modified und Range-Support via Werkzeug
    resp = make_response(send_file(
        path,
        mimetype=f.mime_type,
        as_attachment=False,
        conditional=True,
        etag=True,
        last_modified=dt.datetime.utcfromtimestamp(path.stat().st_mtime)
    ))
    resp.headers["Accept-Ranges"] = "bytes"
    # Für Einbettung: optional Caching für z.B. 1 Tag (feintunen)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    # Optional inline Name
    resp.headers["Content-Disposition"] = f'inline; filename="{f.orig_filename}"'
    return resp

if __name__ == "__main__":
    app.run(debug=True)
