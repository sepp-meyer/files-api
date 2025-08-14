# fileserver/renderers.py
from pathlib import Path
from typing import Literal, Tuple

Kind = Literal["audio", "video", "image", "pdf", "other"]

def detect_kind(mime: str | None, ext: str | None) -> Kind:
    m = (mime or "").lower()
    e = (ext or "").lower()
    if m.startswith("audio/") or e in {"mp3", "wav", "flac", "m4a"}:
        return "audio"
    if m.startswith("video/") or e in {"mp4", "webm"}:
        return "video"
    if m == "application/pdf" or e == "pdf":
        return "pdf"
    if m.startswith("image/") or e in {"png", "jpg", "jpeg", "gif"}:
        return "image"
    return "other"

def embed_html(kind: Kind, src: str) -> str:
    if kind == "video":
        return f'<video controls preload="metadata" width="640" src="{src}"></video>'
    if kind == "audio":
        return f'<audio controls preload="metadata" src="{src}"></audio>'
    if kind == "image":
        return f'<img src="{src}" alt="" style="max-width:100%;height:auto;">'
    if kind == "pdf":
        # Iframe reicht i.d.R.; Browser-PDF-Viewer lädt anhand Content-Type
        return f'<iframe src="{src}" width="100%" height="600" style="border:1px solid #eee;border-radius:8px;"></iframe>'
    # Fallback: Link
    return f'<a href="{src}" target="_blank" rel="noopener">Datei öffnen</a>'

# Übersicht für Admin-Seite
RENDER_MATRIX = [
    {"kind": "audio", "extensions": "mp3, wav, flac", "html": embed_html("audio", "{{SRC}}")},
    {"kind": "video", "extensions": "mp4", "html": embed_html("video", "{{SRC}}")},
    {"kind": "image", "extensions": "png, jpg, jpeg, gif", "html": embed_html("image", "{{SRC}}")},
    {"kind": "pdf",   "extensions": "pdf", "html": embed_html("pdf", "{{SRC}}")},
]
