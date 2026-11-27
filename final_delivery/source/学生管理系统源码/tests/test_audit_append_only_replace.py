"""SQLite REPLACE must not silently delete and replace an existing audit."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


@pytest.mark.parametrize("schema_source", ["metadata", "migration"])
def test_replace_cannot_overwrite_existing_audit(tmp_path, schema_source):
    from app import create_app
    from app.extensions import db

    database = tmp_path / "replace.sqlite"
    application = create_app("testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}"},
                             instance_path=str(tmp_path / "instance"))
    if schema_source == "migration":
        result = application.test_cli_runner().invoke(args=["db", "upgrade"])
        assert result.exit_code == 0, result.output
    with application.app_context():
        if schema_source == "metadata":
            db.create_all()
        db.session.execute(text("INSERT INTO audit_logs (audit_id,entity_type,entity_id,action) "
                                "VALUES (101,'Student',1,'create')"))
        db.session.commit()
        with pytest.raises(IntegrityError, match="append-only"):
            db.session.execute(text("INSERT OR REPLACE INTO audit_logs "
                                    "(audit_id,entity_type,entity_id,action) "
                                    "VALUES (101,'Student',999,'delete')"))
            db.session.commit()
        db.session.rollback()
        assert db.session.execute(text("SELECT entity_id,action FROM audit_logs WHERE audit_id=101")).one() == (1, "create")
        assert db.session.execute(text("PRAGMA recursive_triggers")).scalar() == 1
        db.session.remove()
        db.engine.dispose()
