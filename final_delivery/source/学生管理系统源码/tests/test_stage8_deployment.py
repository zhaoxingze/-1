from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db


def test_empty_demo_migration_and_cli_repeat(tmp_path, monkeypatch):
    monkeypatch.delenv("SMS_DATABASE_URI", raising=False)
    instance = tmp_path / "isolated demo"
    app = create_app("demo", instance_path=str(instance))
    database = instance / "student_management.db"
    assert not database.exists()
    runner = app.test_cli_runner()

    def run(args, input=None):
        result = runner.invoke(args=args, input=input)
        assert result.exit_code == 0, result.output
        return result.output

    run(["db", "upgrade"])
    run(["db", "upgrade"])
    run(["db", "check"])
    assert "added 3" in run(["seed-roles"])
    assert "added 0" in run(["seed-roles"])
    password = "Only-fixture-deployment-803"
    assert password not in run(["create-admin"], input=f"isolated_admin\n{password}\n{password}\n")
    duplicate = runner.invoke(args=["create-admin"], input="isolated_admin\n")
    assert duplicate.exit_code != 0
    assert "added 10" in run(["seed-demo"])
    assert "added 0" in run(["seed-demo"])
    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert len(tables) == 13
        assert sum(len(inspector.get_columns(table)) for table in tables) == 94
        assert sum(len(inspector.get_foreign_keys(table)) for table in tables) == 20
        assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert db.session.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        assert db.session.execute(text("PRAGMA foreign_key_check")).all() == []
        assert db.session.execute(text("SELECT COUNT(*) FROM sqlite_schema WHERE type='trigger'")).scalar() == 7
        assert db.session.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1
        db.session.remove()
        db.engine.dispose()
    client = app.test_client()
    assert client.get("/health").json["status"] == "ok"
    assert client.get("/static/vendor/bootstrap-5.3.3.min.css").status_code == 200
    assert "console" not in {rule.endpoint for rule in app.url_map.iter_rules()}


def test_create_admin_rejects_out_of_range_username(db_app):
    runner = db_app.test_cli_runner()
    assert runner.invoke(args=["seed-roles"]).exit_code == 0
    result = runner.invoke(args=["create-admin"], input=f"{'x' * 51}\nFixture-only!\nFixture-only!\n")
    assert result.exit_code != 0
    with db_app.app_context():
        assert db.session.execute(text("SELECT COUNT(*) FROM users")).scalar() == 0
