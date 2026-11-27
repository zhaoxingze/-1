"""Configuration profiles; no database connections or business policy."""

from datetime import timedelta


class Config:
    ACTIVE_SEMESTER = "2026-Fall"
    TESTING = False
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"hide_parameters": True}
    MAX_CONTENT_LENGTH = 1024 * 1024
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = False
    SESSION_PROTECTION = "strong"
    LOG_LEVEL = "INFO"


class DevelopmentConfig(Config):
    DEBUG = True
    # Flask-SQLAlchemy resolves a relative SQLite URI inside app.instance_path.
    SQLALCHEMY_DATABASE_URI = "sqlite:///student_management.db"


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "stage1-tests-only-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LOG_LEVEL = "WARNING"


class DemoConfig(Config):
    TRUSTED_HOSTS = ["127.0.0.1", "localhost"]
    SQLALCHEMY_DATABASE_URI = "sqlite:///student_management.db"


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///student_management.db"


CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "demo": DemoConfig,
           "production": ProductionConfig}
