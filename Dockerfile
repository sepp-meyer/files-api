# syntax=docker/dockerfile:1

############################
# 1) Builder: Dependencies
############################
FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

############################
# 2) Runtime (Plesk-ready)
############################
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Build-Args (Defaults)
ARG SECRET_KEY=change-me
ARG DOWNLOAD_HMAC_SECRET=also-change-me
ARG ADMIN_USERNAME=admin
ARG ADMIN_PASSWORD=changeme
ARG STORAGE_DIR=/data/storage
ARG DATABASE_URL=sqlite:////data/app.db
ARG PREFERRED_URL_SCHEME=https
ARG FLASK_DEBUG=0
ARG CORS_ORIGINS=

# ENV (Plesk liest sie im Run-Dialog)
ENV SECRET_KEY=${SECRET_KEY} \
    DOWNLOAD_HMAC_SECRET=${DOWNLOAD_HMAC_SECRET} \
    ADMIN_USERNAME=${ADMIN_USERNAME} \
    ADMIN_PASSWORD=${ADMIN_PASSWORD} \
    STORAGE_DIR=${STORAGE_DIR} \
    DATABASE_URL=${DATABASE_URL} \
    PREFERRED_URL_SCHEME=${PREFERRED_URL_SCHEME} \
    FLASK_DEBUG=${FLASK_DEBUG} \
    CORS_ORIGINS=${CORS_ORIGINS}

# venv + App
COPY --from=builder /opt/venv /opt/venv
COPY . .

# /data vorbereiten
RUN mkdir -p /data /data/storage
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/healthz', timeout=3).read(); print('ok')"]

# Gunicorn mit --preload: App-Init (inkl. Admin-Setup) läuft nur einmal im Master
CMD ["gunicorn", "--preload", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8000", "--timeout", "60", "fileserver.app:create_app()"]

