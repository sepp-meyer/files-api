# test_flow.py
import os
import io
import time
import json
import random
import string
import tempfile
from urllib.parse import urljoin
import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

def wait_for_server(url: str, timeout=10.0):
    print(f"[1/9] Warte auf Server {url} ...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1.5)
            if r.status_code < 500:
                print("      Server erreichbar.")
                return True
        except Exception:
            pass
        time.sleep(0.3)
    print("      ⚠ Server nicht erreichbar. Prüfe, ob `python3 app.py` läuft.")
    return False

def create_token(session: requests.Session):
    print("[2/9] Erzeuge API-Token ...")
    url = urljoin(BASE_URL, "/admin/tokens")
    data = {"name": "test-client", "days": "1", "scopes": "read"}
    r = session.post(url, data=data, timeout=10)
    r.raise_for_status()
    payload = r.json()
    token = payload["token"]
    print(f"      OK. Token: {token}")
    return token

def random_title():
    letters = string.ascii_lowercase + string.digits
    return "testfile-" + "".join(random.choice(letters) for _ in range(8))

def upload_test_file(session: requests.Session, title: str):
    print("[3/9] Lade Testdatei hoch ...")
    url = urljoin(BASE_URL, "/upload")

    # kleine Dummy-"mp3"-Datei (Inhalt ist egal; Endung zählt für MIME)
    fake_mp3 = io.BytesIO(b"ID3\x03\x00\x00\x00\x00\x00\x00TEST-DATA-" + os.urandom(256))
    files = {"file": ("test_upload.mp3", fake_mp3, "audio/mpeg")}
    data = {"title": title, "year": "2025"}

    r = session.post(url, files=files, data=data, timeout=30, allow_redirects=True)
    if r.status_code not in (200, 302):
        raise RuntimeError(f"Upload fehlgeschlagen: HTTP {r.status_code}")
    print(f"      OK. Titel='{title}' hochgeladen.")
    return True

def find_uploaded_by_title(session: requests.Session, token: str, title: str):
    print("[4/9] Suche hochgeladene Datei per API ...")
    url = urljoin(BASE_URL, f"/api/files?token={token}")
    r = session.get(url, timeout=10)
    r.raise_for_status()
    items = r.json()
    for item in items:
        if item.get("title") == title:
            print(f"      Gefunden: UUID={item['id']}, MIME={item['mime_type']}, Größe={item['size_bytes']}")
            return item
    raise RuntimeError("Hochgeladene Datei in /api/files nicht gefunden.")

def fetch_meta(session: requests.Session, token: str, file_id: str):
    print("[5/9] Hole Metadaten ...")
    url = urljoin(BASE_URL, f"/api/files/{file_id}?token={token}")
    r = session.get(url, timeout=10)
    r.raise_for_status()
    meta = r.json()
    print("      Meta:", json.dumps(meta, indent=2, ensure_ascii=False))
    return meta

def fetch_signed_url(session: requests.Session, token: str, file_id: str):
    print("[6/9] Hole kurzlebige signierte URL ...")
    url = urljoin(BASE_URL, f"/api/files/{file_id}/signed-url?token={token}")
    r = session.get(url, timeout=10)
    r.raise_for_status()
    payload = r.json()
    signed = payload["download_url"]
    exp = payload["exp"]
    print(f"      OK. signed_url (exp={exp}): {signed}")
    return signed

def check_embed_redirect(session: requests.Session, token: str, file_id: str):
    print("[7/9] Teste /api/embed Redirect ...")
    url = urljoin(BASE_URL, f"/api/embed/{file_id}?token={token}")
    r = session.get(url, allow_redirects=False, timeout=10)
    if r.status_code != 302 or "Location" not in r.headers:
        raise RuntimeError(f"Unerwartete Antwort von /api/embed: {r.status_code}")
    location = r.headers["Location"]
    print(f"      302 Location: {location}")
    return location

def range_request_first_100(session: requests.Session, download_url: str):
    print("[8/9] Range-Request (erste 100 Bytes) ...")
    r = session.get(download_url, headers={"Range": "bytes=0-99"}, timeout=20)
    if r.status_code not in (200, 206):
        raise RuntimeError(f"Range-Request fehlgeschlagen: HTTP {r.status_code}")
    size = len(r.content)
    print(f"      OK. Empfangene Bytes: {size} (Status {r.status_code})")
    return size

def write_embed_html(file_id: str, token: str, path="embed_test.html"):
    print("[9/9] Schreibe embed_test.html ...")
    html = f"""<!doctype html>
<html lang="de">
  <meta charset="utf-8">
  <title>Embed Test</title>
  <h1>Audio Embed vom Fileserver</h1>
  <audio controls preload="metadata"
         src="{BASE_URL}/api/embed/{file_id}?token={token}"></audio>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"      OK. Datei geschrieben: {os.path.abspath(path)}")
    return path

def main():
    if not wait_for_server(BASE_URL):
        return

    s = requests.Session()

    try:
        token = create_token(s)
        title = random_title()
        upload_test_file(s, title)
        item = find_uploaded_by_title(s, token, title)
        file_id = item["id"]
        fetch_meta(s, token, file_id)
        signed = fetch_signed_url(s, token, file_id)
        location = check_embed_redirect(s, token, file_id)
        range_request_first_100(s, location)
        write_embed_html(file_id, token)

        print("\n✅ Test erfolgreich abgeschlossen.")
        print(f"   • UUID: {file_id}")
        print(f"   • Token: {token}")
        print(f"   • Signed URL: {signed}")
        print(f"   • Embed-HTML: {os.path.abspath('embed_test.html')}")
        print("\nÖffne jetzt 'embed_test.html' im Browser und prüfe die Wiedergabe.")
    except Exception as e:
        print("\n❌ Test fehlgeschlagen:", e)

if __name__ == "__main__":
    main()
