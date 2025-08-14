# fileserver/routes/__init__.py
from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')  # << Präfix
api_bp = Blueprint('api', __name__, url_prefix='/api')

from . import admin, api  # noqa: E402,F401
