import time
import pytest


def test_login_discards_preexisting_session_state(auth):
    with auth.client.session_transaction() as session:
        session["untrusted_old_state"] = "injected"
    auth.login()
    with auth.client.session_transaction() as session:
        assert "untrusted_old_state" not in session
        assert session["_permanent"] is True
        assert session["_auth_issued_at"] <= time.time()


@pytest.mark.parametrize("issued_at", [None, "bad", True, 0, -1, float("nan"), float("inf")])
def test_invalid_session_timestamps_are_rejected(auth, issued_at):
    auth.login()
    with auth.client.session_transaction() as session:
        session["_auth_issued_at"] = issued_at
    assert auth.client.get("/profile").status_code == 302


def test_expired_and_future_session_rejected(auth):
    for issued_at in (time.time()-1801, time.time()+120):
        auth.login()
        with auth.client.session_transaction() as session:
            session["_auth_issued_at"] = issued_at
        assert auth.client.get("/profile").status_code == 302


@pytest.mark.parametrize("change", ["disable", "delete", "password", "role", "binding"])
def test_database_identity_changes_invalidate_existing_session(auth, change):
    from app.extensions import db
    from app.models import User, Role
    from sqlalchemy import text
    from werkzeug.security import generate_password_hash
    auth.login("auth_student")
    with auth.app.app_context():
        user = db.session.get(User, auth.ids["auth_student"])
        if change == "disable": user.is_active = False
        elif change == "delete": db.session.delete(user)
        elif change == "password": user.password_hash = generate_password_hash("changed-only-in-tests")
        elif change == "role":
            role = db.session.get(Role, 17)
            user.student = None; user.role = role
        else:
            # Deliberately bypass ORM to simulate inconsistent legacy data.
            db.session.execute(text("UPDATE users SET student_id=NULL WHERE user_id=:id"), {"id": user.user_id})
        db.session.commit()
    assert auth.client.get("/profile").status_code == 302


@pytest.mark.parametrize("identity", ["not-int", "-2", "99999999999999999999999999999999999999", 1, True, None])
def test_malformed_session_identity_fails_closed(auth, identity):
    auth.login()
    with auth.client.session_transaction() as session:
        session["_user_id"] = identity
    assert auth.client.get("/profile").status_code == 302


def test_cookie_tampering_does_not_authenticate(auth):
    auth.login()
    cookie = auth.client.get_cookie("session").value
    auth.client.set_cookie("session", cookie + "tamper")
    assert auth.client.get("/admin/").status_code == 302


@pytest.mark.parametrize("version", ["非ASCII", "", None, 123, "x"*65])
def test_invalid_credential_version_is_rejected_without_error(auth, version):
    auth.login()
    with auth.client.session_transaction() as session:
        session["_auth_version"] = version
    assert auth.client.get("/profile").status_code == 302


def test_browser_identity_change_requires_new_login(auth):
    auth.login()
    assert auth.client.get("/profile", headers={"User-Agent":"different-browser"}).status_code == 302


def test_development_cookie_flags_and_absolute_lifetime(auth):
    response = auth.login()
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Secure;" not in cookie
    assert auth.app.config["PERMANENT_SESSION_LIFETIME"].total_seconds() == 1800
    assert auth.app.config["SESSION_REFRESH_EACH_REQUEST"] is False


def test_production_requires_secret_and_sets_secure_cookie(monkeypatch, tmp_path):
    from app import create_app
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app("production", instance_path=str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "a-production-only-secret-from-environment")
    app = create_app("production", instance_path=str(tmp_path))
    assert not app.debug and not app.testing
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["WTF_CSRF_ENABLED"] is True
