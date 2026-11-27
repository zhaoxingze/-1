"""Request-scoped account loading, bounded sessions and safe local redirects."""

import hashlib
import hmac
import json
import math
import posixpath
import time
from pathlib import Path
from urllib.parse import unquote, urlencode, urlsplit

from flask import current_app, redirect, request, session, url_for
from flask_login import current_user
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, login_manager
from app.models import AuditLog, User
from app.services.data_validation_service import validate_user_profile_binding


def credential_version(user: User) -> str:
    """Opaque version; hashes and role claims are never stored in the cookie."""
    state = [user.user_id, user.password_hash, user.role_id, user.role.name,
             user.student_id, user.teacher_id]
    latest_identity_change = db.session.scalar(select(func.max(AuditLog.audit_id)).where(
        AuditLog.entity_type == "User", AuditLog.entity_id == user.user_id,
        or_(AuditLog.action == "status_change",
            and_(AuditLog.action == "update", AuditLog.after_data["identity_changed"].as_boolean().is_(True))),
    ))
    if latest_identity_change is not None:
        state.append(latest_identity_change)
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, json.dumps(state).encode(), hashlib.sha256).hexdigest()


def account_is_usable(user: User | None) -> bool:
    if user is None or not user.is_active:
        return False
    try:
        validate_user_profile_binding(user)
    except ValueError:
        return False
    return True


def safe_next(target: str | None) -> str | None:
    """Accept local absolute paths only, including after URL decoding."""
    if not isinstance(target, str) or len(target) > 2048:
        return None
    decoded = target
    for _ in range(8):
        expanded = unquote(decoded)
        if expanded == decoded:
            break
        decoded = expanded
    else:
        return None
    if (not decoded.startswith("/") or decoded.startswith("//") or "\\" in decoded
            or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
        return None
    try:
        parsed = urlsplit(decoded)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    if posixpath.normpath(parsed.path) in {"/login", "/logout"}:
        return None
    return target


def configure_auth(app) -> None:
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(identity):
        issued_at = session.get("_auth_issued_at")
        version = session.get("_auth_version")
        now = time.time()
        valid_identity = (isinstance(identity, str) and identity.isascii()
                          and identity.isdecimal() and 0 < len(identity) <= 19
                          and 0 < int(identity) <= 9223372036854775807)
        valid_time = (isinstance(issued_at, (int, float)) and not isinstance(issued_at, bool)
                      and math.isfinite(issued_at) and 0 <= now - issued_at
                      < current_app.permanent_session_lifetime.total_seconds())
        if (not valid_identity or not valid_time or not isinstance(version, str)
                or not version.isascii() or len(version) != 64
                or session.get("_fresh") is not True):
            session.clear()
            return None
        # An old signed cookie must not create a missing development database
        # merely because the public layout asks for current_user.
        database = db.engine.url.database
        if (db.engine.dialect.name == "sqlite" and database and database != ":memory:"
                and not db.engine.url.query.get("uri") and not Path(database).is_file()):
            session.clear()
            return None
        try:
            with db.session.no_autoflush:
                user = db.session.get(User, int(identity))
                if not account_is_usable(user) or not hmac.compare_digest(version, credential_version(user)):
                    session.clear()
                    return None
        except SQLAlchemyError:
            db.session.rollback()
            session.clear()
            current_app.logger.warning("security.identity_store_unavailable")
            return None
        return user

    @login_manager.unauthorized_handler
    def unauthorized():
        # Use the path, never an attacker-controlled Host header or absolute URL.
        target = safe_next(request.full_path.rstrip("?")) or "/dashboard"
        return redirect(url_for("auth.login") + "?" + urlencode({"next": target}))

    @app.after_request
    def protect_private_responses(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        if response.mimetype == "text/html":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "same-origin"
        if request.endpoint in {"static", "dashboard.health"}:
            return response
        if request.blueprint == "auth" or current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response
