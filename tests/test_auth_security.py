import pytest


@pytest.mark.parametrize("next_url", ["https://evil.example/x", "//evil.example", "///evil.example", "\\\\evil.example", "/\\evil.example", "javascript:alert(1)", "/%2f%2fevil.example", "/%5cevil.example", "/%252f%252fevil.example", "/%0d%0aLocation:evil", "/login", "/logout", "/login?next=/admin/"])
def test_unsafe_redirects_fall_back_to_dashboard(auth, next_url):
    response = auth.login(next_url=next_url)
    assert response.status_code == 303
    assert response.location == "/dashboard"


def test_safe_relative_next_is_preserved(auth):
    response = auth.login(next_url="/profile?tab=basic")
    assert response.location == "/profile?tab=basic"


def test_login_csrf_and_invalid_input(auth):
    assert auth.client.post("/login", data={"username": "auth_admin", "password": auth.password}).status_code == 400
    for username,password in (("", ""), ("a"*51,"bad"), ("auth_admin","p"*1025), ("' OR 1=1 --", "bad")):
        response = auth.login(username,password)
        assert response.status_code == 200
        with auth.client.session_transaction() as session:
            assert "_user_id" not in session


def test_logs_and_html_do_not_expose_credentials(auth, caplog):
    import logging
    with caplog.at_level(logging.INFO):
        auth.login()
        response = auth.client.get("/profile")
    assert auth.password not in response.text + caplog.text
    assert "scrypt:" not in response.text + caplog.text
    assert "password_hash" not in response.text
    assert "no-store" in response.headers["Cache-Control"]


def test_forged_role_and_identity_parameters_are_ignored(auth):
    response = auth.login("auth_student", role_id="17", user_id=str(auth.ids["auth_admin"]))
    assert response.status_code == 303
    assert auth.client.get("/admin/?role_id=17&user_id=1").status_code == 403
    assert "auth_student" in auth.client.get("/profile?user_id=1").text


@pytest.mark.parametrize("database_kind", ["memory", "missing-file"])
def test_old_valid_cookie_does_not_break_public_pages_when_database_uninitialized(auth, tmp_path, database_kind):
    from app import create_app
    from app.extensions import db
    auth.login()
    old_cookie = auth.client.get_cookie("session").value
    target = tmp_path / "not-initialized.sqlite"
    uri = "sqlite:///:memory:" if database_kind == "memory" else f"sqlite:///{target.as_posix()}"
    application=create_app("testing", {"SQLALCHEMY_DATABASE_URI":uri},instance_path=str(tmp_path / "uninitialized"))
    client=application.test_client();client.set_cookie("session",old_cookie)
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/profile").status_code == 302
    assert not target.exists()
    with application.app_context():
        db.session.remove();db.engine.dispose()


@pytest.mark.parametrize("path", ["/students/9223372036854775808/profile", "/admin/users/9223372036854775808/reset-password"])
def test_oversized_resource_ids_are_handled_as_missing(auth, path):
    auth.login()
    assert auth.client.get(path).status_code == 404
