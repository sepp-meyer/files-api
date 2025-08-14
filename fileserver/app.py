import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv, find_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config, get_cors_resources
from .models import db, AdminUser
from .routes import admin_bp, api_bp

# .env laden – sucht im Projekt (robuster)
load_dotenv(find_dotenv())

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Reverse Proxy (Plesk) korrekt auswerten (Scheme/Host/Port)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_initial_admin(app)

    CORS(app, resources=get_cors_resources())

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    return app

def _ensure_initial_admin(app: Flask):
    """
    Legt einen Admin an, wenn ADMIN_USERNAME + ADMIN_PASSWORD gesetzt sind
    und der User noch nicht existiert. Setze diese Variablen in Plesk/Docker.
    """
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if username and password:
        AdminUser.create_or_update(username=username, password=password)
        app.logger.info("Admin-User ist bereit (username='%s').", username)
    else:
        app.logger.warning("Kein ADMIN_USERNAME/ADMIN_PASSWORD gesetzt – Admin-Login wäre ohne vorhandene User nicht möglich.")
