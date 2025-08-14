# Fileserver (PoC)

Zweck: Medien speichern und über eine kleine API/Einbettung bereitstellen.  
Admin-UI: Upload, Metadaten, Embed-Snippets, Token-Verwaltung.

## Unterstützte Dateitypen

Default (konfigurierbar via `ALLOWED_EXT`):  
`mp3, mp4, wav, pdf, png, jpg, jpeg, gif`

## Einbettung

Öffentlich:  
`/api/embed/<uuid>?token=<apitoken>`

Der Endpunkt erzeugt intern einen kurzlebigen signierten Download-Link (HTTP 302 Redirect).  
Audio/Video/Image/PDF können direkt in HTML verwendet werden:

```html
<!-- audio -->
<audio controls preload="metadata" src="https://example.org/api/embed/<uuid>?token=..."></audio>

<!-- video -->
<video controls preload="metadata" width="640" src="https://example.org/api/embed/<uuid>?token=..."></video>

<!-- image -->
<img src="https://example.org/api/embed/<uuid>?token=..." alt="" />

<!-- pdf -->
<iframe src="https://example.org/api/embed/<uuid>?token=..." width="100%" height="600"></iframe>
```

Hinweise:

* Für das reine Abspielen/Anzeigen sind üblicherweise **keine CORS-Header** nötig (Canvas/Pixel-Reads ausgenommen).
* Downloads liefern korrekten `Content-Type`, `Accept-Ranges` (Seek), ETag.

## Admin-Vorschau (ohne Token)

`/admin/stream/<uuid>` streamt inline direkt aus dem Storage (nur in Admin-UI genutzt).

## Tokens

* Erstellen, **Revoke** und **Delete** im Admin.
* Scopes z. B. `read`. Ablauf optional.

## Konfiguration (env)

* `ALLOWED_EXT` (z. B. `mp3,mp4,wav,pdf,png,jpg,jpeg,gif`)
* `CORS_ORIGINS` (leer = `*` auf `/api/*`)
* `DOWNLOAD_HMAC_SECRET`, `SECRET_KEY`, `DATABASE_URL`, `STORAGE_DIR`

## Rendering-Übersicht

Siehe Admin-Menü „Rendering“. Dort sind alle Render-Varianten dokumentiert.