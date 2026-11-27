import pytest


def test_login_form_is_public_and_has_no_store_header(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert 'name="password"' in response.text
    assert 'name="csrf_token"' in response.text
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.parametrize("username,path", [("auth_admin", "/admin/"), ("auth_teacher", "/dashboard/teacher"), ("auth_student", "/dashboard/student")])
def test_real_hash_login_and_role_landing(auth, username, path):
    response = auth.login(username)
    assert response.status_code == 303
    assert response.location == "/dashboard"
    assert auth.client.get(path).status_code == 200
    assert auth.client.get("/dashboard").location == path
    with auth.client.session_transaction() as session:
        assert session["_user_id"] == str(auth.ids[username])
        assert "role_id" not in session
        assert "password_hash" not in session


@pytest.mark.parametrize("username,password", [("auth_admin", "wrong"), ("no-such-user", "wrong"), ("disabled", "Only-for-isolated-tests!42")])
def test_invalid_credentials_have_same_message_and_no_auth_session(auth, username, password):
    response = auth.login(username, password)
    assert response.status_code == 200
    assert "用户名或密码错误，或账号不可用。" in response.text
    assert password not in response.text
    assert "password_hash" not in response.text
    with auth.client.session_transaction() as session:
        assert "_user_id" not in session


def test_archived_or_graduated_student_keeps_independent_active_account(auth):
    from app.extensions import db
    from app.models import Student
    with auth.app.app_context():
        student = db.session.get(Student, auth.student_ids[0])
        student.is_archived = True; student.status = "graduated"; db.session.commit()
    assert auth.login("auth_student").status_code == 303
    assert auth.client.get("/profile").status_code == 200
