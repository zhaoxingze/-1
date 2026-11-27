"""Application factory for the student information management system."""

import os
import secrets
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from flask import Flask

from config import CONFIGS

from .extensions import csrf, db, login_manager, migrate


def create_app(
    config_name: str = "development", test_config: Mapping[str, Any] | None = None,
    *, instance_path: str | None = None,
) -> Flask:
    """Create an independent app without creating tables, users, or records."""
    if config_name not in CONFIGS:
        raise ValueError(f"Unknown configuration: {config_name}")

    if config_name == "demo" and instance_path is None:
        instance_path = str(Path(__file__).resolve().parent.parent / "instance" / "demo")
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
    app.config.from_object(CONFIGS[config_name])
    if config_name in {"development", "demo", "production"}:
        if "ACTIVE_SEMESTER" in os.environ:
            app.config["ACTIVE_SEMESTER"] = os.environ["ACTIVE_SEMESTER"]
        if config_name != "demo":
            app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
        if os.environ.get("SMS_DATABASE_URI"):
            app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SMS_DATABASE_URI"]
    if test_config is not None:
        app.config.update(test_config)
    if config_name == "demo":
        app.config.update(SECRET_KEY=secrets.token_hex(32), DEBUG=False, TESTING=False, SESSION_COOKIE_SECURE=False)
    semester = app.config["ACTIVE_SEMESTER"]
    if not isinstance(semester, str) or not semester.strip() or len(semester) > 30 or "\x00" in semester:
        raise ValueError("ACTIVE_SEMESTER must be a nonblank label of at most 30 characters")
    app.config["ACTIVE_SEMESTER"] = semester.strip()
    if config_name == "production" and not os.environ.get("SECRET_KEY"):
        raise ValueError("Production requires SECRET_KEY in the environment")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from .logging_config import configure_logging

    configure_logging(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401 -- register all model metadata, never create tables

    from .auth.session import configure_auth

    configure_auth(app)

    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parent.parent / "migrations"))

    from .academics import bp as academics_bp
    from .admin import bp as admin_bp
    from .attendance import bp as attendance_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .records import bp as records_bp
    from .students import bp as students_bp

    for blueprint in (
        auth_bp, admin_bp, students_bp, academics_bp,
        attendance_bp, records_bp, dashboard_bp,
    ):
        app.register_blueprint(blueprint)

    from .errors import register_error_handlers

    register_error_handlers(app)
    from .cli import register_cli

    register_cli(app)
    app.logger.info("Application initialized: profile=%s; business tables not created", config_name)
    return app
