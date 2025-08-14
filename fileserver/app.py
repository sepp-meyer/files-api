import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from config import Config, get_cors_resources
from models import db
from routes import admin_bp, api_bp

# .env laden (falls vorhanden)
load_dotenv()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    CORS(app, resources=get_cors_resources())

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    return app
