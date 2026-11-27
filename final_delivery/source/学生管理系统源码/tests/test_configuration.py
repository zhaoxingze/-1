"""Configuration, extension boundaries, and stage 1 side-effect checks."""

from pathlib import Path

import pytest
from sqlalchemy import inspect


def test_development_and_testing_use_separate_database_targets(monkeypatch, tmp_path):
    from app import create_app
    from app.extensions import db

    monkeypatch.setenv("SECRET_KEY", "environment-development-key")
    development = create_app("development", instance_path=str(tmp_path / "development"))
    testing = create_app("testing")
    assert development.testing is False
    assert development.debug is True
    assert testing.testing is True
    assert testing.debug is False
    assert development.secret_key == "environment-development-key"
    assert testing.secret_key != development.secret_key
    with development.app_context():
        database_path = Path(db.engine.url.database)
        assert database_path == Path(development.instance_path) / "student_management.db"
        assert not database_path.exists()
        db.engine.dispose()
    with testing.app_context():
        assert db.engine.url.database == ":memory:"
        assert inspect(db.engine).get_table_names() == []
        db.engine.dispose()
    assert not database_path.exists()


def test_configuration_overrides_apply_before_extension_initialization():
    from app import create_app
    from app.extensions import db

    application = create_app("testing", {"SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with application.app_context():
        assert db.engine.url.database is None
        db.engine.dispose()


def test_unknown_configuration_is_rejected():
    from app import create_app

    with pytest.raises(ValueError, match="Unknown configuration"):
        create_app("not-a-config")


def test_expected_blueprints_and_extensions_are_initialized(app):
    from app.extensions import csrf, db, login_manager

    assert set(app.blueprints) == {
        "auth", "admin", "students", "academics", "attendance", "records", "dashboard"
    }
    assert app.extensions["sqlalchemy"] is db
    assert app.extensions["csrf"] is csrf
    assert app.login_manager is login_manager


def test_public_pages_do_not_create_database_or_business_tables(tmp_path):
    from app import create_app
    from app.extensions import db

    application = create_app("development", instance_path=str(tmp_path / "development"))
    with application.app_context():
        database_path = Path(db.engine.url.database)
        assert not database_path.exists()
        # Stage 2 registers metadata; factory/public pages still must not create tables.
        assert len(db.metadata.tables) == 13
    client = application.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200
    assert not database_path.exists()
    with application.app_context():
        db.engine.dispose()


@pytest.mark.parametrize("path", ["/auth/login", "/students", "/courses", "/_test/forbidden"])
def test_business_and_debug_routes_are_not_exposed(client, path):
    assert client.get(path).status_code == 404


def test_creating_multiple_apps_does_not_duplicate_log_handlers():
    from app import create_app
    from app.extensions import db

    first = create_app("testing")
    handler_count = len(first.logger.handlers)
    second = create_app("testing")
    assert len(second.logger.handlers) == handler_count
    for application in (first, second):
        with application.app_context():
            db.engine.dispose()
