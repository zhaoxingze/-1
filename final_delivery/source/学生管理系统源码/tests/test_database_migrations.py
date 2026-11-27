"""Exercise the actual initial Alembic revision against a fresh SQLite file."""

from sqlalchemy import inspect, text


def test_empty_database_upgrade_matches_metadata_and_can_repeat(tmp_path):
    from app import create_app
    from app.extensions import db

    database = tmp_path / "migration.sqlite"
    application = create_app("testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}"},
                             instance_path=str(tmp_path / "instance"))
    assert not database.exists()
    runner = application.test_cli_runner()
    upgraded = runner.invoke(args=["db", "upgrade"])
    assert upgraded.exit_code == 0, upgraded.output
    with application.app_context():
        inspector = inspect(db.engine)
        assert set(inspector.get_table_names()) == set(db.metadata.tables) | {"alembic_version"}
        assert len(db.metadata.tables) == 13
        assert sum(len(t.columns) for t in db.metadata.tables.values()) == 94
        assert sum(len(inspector.get_foreign_keys(name)) for name in db.metadata.tables) == 20
        for name, table in db.metadata.tables.items():
            assert {c["name"] for c in inspector.get_columns(name)} == set(table.columns.keys())
        assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert db.session.execute(text("PRAGMA foreign_key_check")).all() == []
        assert len(db.session.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).all()) >= 6
        db.session.remove()
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    drift = runner.invoke(args=["db", "check"])
    assert drift.exit_code == 0, drift.output
    with application.app_context():
        db.engine.dispose()
