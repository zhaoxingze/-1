from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from app import create_app
from app.extensions import db


def test_online_backup_includes_committed_wal_and_restores_independently(tmp_path):
    from scripts.sqlite_snapshot import copy_database

    source, backup, target = [tmp_path / f"{stem}.sqlite" for stem in ("live", "backup", "restored")]
    with closing(sqlite3.connect(source)) as writer:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("CREATE TABLE example (identifier INTEGER PRIMARY KEY)")
        writer.execute("INSERT INTO example VALUES (1)")
        writer.commit()
        assert Path(f"{source}-wal").stat().st_size > 0
        writer.execute("INSERT INTO example VALUES (2)")
        report = copy_database(source, backup)
        writer.rollback()
    assert report["integrity_check"] == "ok" and report["foreign_key_violations"] == 0
    assert len(report["sha256"]) == 64
    copy_database(backup, target)
    with closing(sqlite3.connect(target)) as restored:
        assert restored.execute("SELECT * FROM example").fetchall() == [(1,)]
        restored.execute("INSERT INTO example VALUES (3)")
        restored.commit()
    with closing(sqlite3.connect(backup)) as saved:
        assert saved.execute("SELECT * FROM example").fetchall() == [(1,)]


def test_backup_preserves_existing_target_and_rejects_invalid_source(tmp_path):
    from scripts.sqlite_snapshot import copy_database

    source, existing, target = [tmp_path / f"{stem}.sqlite" for stem in ("source", "existing", "target")]
    with closing(sqlite3.connect(source)) as db:
        db.execute("CREATE TABLE sample (value INTEGER)")
    existing.write_bytes(b"preserve existing data")
    for path in (source, existing):
        with pytest.raises(FileExistsError):
            copy_database(source, path)
    assert existing.read_bytes() == b"preserve existing data"
    with pytest.raises(ValueError):
        copy_database(existing, target)
    assert not target.exists()


def test_copy_cleans_up_snapshot_with_foreign_key_violations(tmp_path):
    from scripts.sqlite_snapshot import copy_database

    source, target = tmp_path / "invalid.sqlite", tmp_path / "snapshot.sqlite"
    with closing(sqlite3.connect(source)) as db:
        db.executescript("CREATE TABLE parents (id INTEGER PRIMARY KEY); "
                         "CREATE TABLE children (parent_id INTEGER REFERENCES parents(id)); "
                         "INSERT INTO children VALUES (9000);")
    with pytest.raises(ValueError, match="foreign key"):
        copy_database(source, target)
    assert not target.exists()


def test_restored_app_authorizes_original_account_and_reads_course(auth, tmp_path):
    from scripts.sqlite_snapshot import copy_database

    with auth.app.app_context():
        source = Path(db.engine.url.database)
        runner = auth.app.test_cli_runner()
        assert runner.invoke(args=["seed-demo"]).exit_code == 0
    target = tmp_path / "restored.sqlite"
    copy_database(source, target)
    restored = create_app("demo", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{target.as_posix()}"},
                          instance_path=str(tmp_path / "restore-instance"))
    client = restored.test_client()
    import re

    for username, path, forbidden in [("auth_admin", "/admin/", False), ("auth_student", "/admin/", True)]:
        login = client.get("/login")
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login.text)[1]
        response = client.post("/login", data={"username": username, "password": auth.password, "csrf_token": token})
        assert response.status_code == 303
        assert client.get(path).status_code == (403 if forbidden else 200)
        if not forbidden:
            assert "DEMO-C001" in client.get("/academics/courses").text
        client.delete_cookie("session")
    with restored.app_context():
        db.session.remove()
        db.engine.dispose()
