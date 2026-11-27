"""Isolated applications and clients; no business fixtures or accounts."""

import pytest


@pytest.fixture
def app():
    from app import create_app
    from app.extensions import db

    application = create_app("testing")
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_app(tmp_path):
    """Every database test owns a file under pytest's temporary directory."""
    from app import create_app
    from app.extensions import db

    database_path = tmp_path / "test.sqlite"
    application = create_app(
        "testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}"},
        instance_path=str(tmp_path / "instance"),
    )
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def test_db(db_app):
    from app.extensions import db

    with db_app.app_context():
        yield db
        db.session.rollback()
        db.session.remove()


@pytest.fixture(scope="session")
def auth_password_hash():
    from werkzeug.security import generate_password_hash

    return generate_password_hash("Only-for-isolated-tests!42")


@pytest.fixture
def auth(db_app, auth_password_hash):
    """Fictional accounts in a temporary DB, with deliberately nonstandard role IDs."""
    import re
    from datetime import date
    from types import SimpleNamespace
    from app.extensions import db
    from app.models import Role, Student, Teacher, User

    with db_app.app_context():
        roles = {name: Role(role_id=identity, name=name) for name, identity in
                 (("admin", 17), ("teacher", 29), ("student", 43))}
        teacher = Teacher(teacher_no="AUTH-T1", name="虚构教师")
        students = [Student(student_no=f"AUTH-S{i}", name=f"虚构学生{i}", gender="未指定",
                            enrollment_date=date(2026, 9, 1)) for i in (1, 2)]
        accounts = [User(username="auth_admin", role=roles["admin"], password_hash=auth_password_hash),
                    User(username="auth_teacher", role=roles["teacher"], teacher=teacher, password_hash=auth_password_hash),
                    User(username="auth_student", role=roles["student"], student=students[0], password_hash=auth_password_hash),
                    User(username="other_student", role=roles["student"], student=students[1], password_hash=auth_password_hash),
                    User(username="disabled", role=roles["admin"], is_active=False, password_hash=auth_password_hash)]
        db.session.add_all([*roles.values(), *accounts]); db.session.commit()
        ids = {u.username: u.user_id for u in accounts}
        student_ids = [s.student_id for s in students]
    client = db_app.test_client()

    def token(path="/login"):
        page = client.get(path)
        assert page.status_code == 200, f"CSRF form unavailable: {path}: {page.status_code}"
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.get_data(as_text=True))
        assert match, "Real CSRF token must be present in form"
        return match.group(1)

    def login(username="auth_admin", password="Only-for-isolated-tests!42", next_url=None, **extra):
        path = "/login"
        if next_url is not None:
            from urllib.parse import urlencode
            path += "?" + urlencode({"next": next_url})
        return client.post(path, data={"csrf_token": token(), "username": username, "password": password, **extra})

    return SimpleNamespace(app=db_app, client=client, ids=ids, student_ids=student_ids,
                           token=token, login=login, password="Only-for-isolated-tests!42")
