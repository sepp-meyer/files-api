# fileserver/routes/admin_auth.py
from flask import (
    render_template, request, redirect, url_for, session, g
)
from urllib.parse import urlparse, urljoin
from werkzeug.security import check_password_hash
from . import admin_bp
from ..models import db, AdminUser

SESSION_KEY = "admin_user_id"

def _get_current_admin():
    uid = session.get(SESSION_KEY)
    if not uid:
        return None
    return AdminUser.query.get(uid)

def _is_safe_next(target: str | None) -> bool:
    """
    Erlaubt nur Weiterleitungen innerhalb derselben Domain (gegen Open Redirects).
    """
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return (test.scheme in ("http", "https") and ref.netloc == test.netloc)

# Nur fürs Admin-Blueprint ausführen (nicht global)
@admin_bp.before_request
def require_admin_login():
    g.admin = _get_current_admin()

    # Login-/Logout-Endpoints ohne Login erlauben
    allowed = {"admin.login", "admin.login_post", "admin.logout"}
    if request.endpoint in allowed:
        return

    # Alles andere unter /admin/* nur mit Login
    if not g.admin:
        # „next“ so schlank wie möglich (Pfad inkl. Query)
        next_url = request.full_path if request.query_string else request.path
        return redirect(url_for("admin.login", next=next_url))

@admin_bp.get("/login")
def login():
    if _get_current_admin():
        return redirect(url_for("admin.index"))
    return render_template("admin/login.html", title="Login")

@admin_bp.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_url = request.args.get("next")

    user = AdminUser.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return render_template("admin/login.html", title="Login", error="Ungültige Zugangsdaten."), 401

    session[SESSION_KEY] = user.id

    # sichere Weiterleitung nur auf gleiche Host-Domain
    if _is_safe_next(next_url):
        return redirect(next_url)
    return redirect(url_for("admin.index"))

@admin_bp.get("/logout")
def logout():
    session.pop(SESSION_KEY, None)
    return redirect(url_for("admin.login"))
