from sqlalchemy import select
import pytest


def change_password(auth, old=None, new="Replaced-in-isolated-tests!43"):
    return auth.client.post("/password/change", data={"csrf_token": auth.token("/password/change"),
        "current_password": old or auth.password, "new_password":new, "confirm_password":new})


def test_own_password_change_audited_and_forces_reauthentication(auth):
    from app.extensions import db
    from app.models import User, AuditLog
    from werkzeug.security import check_password_hash
    auth.login("auth_student")
    response = change_password(auth)
    assert response.status_code == 303 and response.location == "/login"
    assert auth.client.get("/profile").status_code == 302
    with auth.app.app_context():
        user = db.session.get(User,auth.ids["auth_student"])
        assert check_password_hash(user.password_hash,"Replaced-in-isolated-tests!43")
        audit = db.session.scalar(select(AuditLog))
        assert audit.action == "update" and audit.actor_user_id == user.user_id
        assert audit.entity_type == "User" and audit.entity_id == user.user_id
        assert "scrypt" not in str(audit.after_data)
        assert "Replaced-in-isolated-tests!43" not in str(audit.after_data)
        assert audit.after_data == {"operation":"self_change", "changed":True}
    assert auth.login("auth_student", "Replaced-in-isolated-tests!43").status_code == 303


def test_wrong_old_password_or_mismatched_confirmation_does_not_change_data(auth):
    from app.extensions import db
    from app.models import AuditLog
    auth.login()
    assert change_password(auth, old="wrong").status_code == 200
    response = auth.client.post("/password/change",data={"csrf_token":auth.token("/password/change"),
        "current_password":auth.password,"new_password":"new","confirm_password":"other"})
    assert response.status_code == 200
    with auth.app.app_context():
        assert db.session.scalar(select(AuditLog)) is None


def test_admin_reset_requires_admin_reauthentication_and_revokes_old_session(auth):
    from app.extensions import db
    from app.models import User, AuditLog
    from werkzeug.security import check_password_hash
    auth.login("auth_student")
    captured_cookie = auth.client.get_cookie("session").value
    auth.client.post("/logout", data={"csrf_token":auth.token("/profile")})
    auth.login()
    path=f"/admin/users/{auth.ids['auth_student']}/reset-password"
    data={"csrf_token":auth.token(path), "admin_password":"wrong", "new_password":"reset-value", "confirm_password":"reset-value"}
    assert auth.client.post(path,data=data).status_code == 200
    data.update(csrf_token=auth.token(path),admin_password=auth.password)
    assert auth.client.post(path,data=data).status_code == 303
    with auth.app.app_context():
        target=db.session.get(User,auth.ids["auth_student"])
        assert check_password_hash(target.password_hash,"reset-value")
        assert target.is_active and target.student_id == auth.student_ids[0]
        assert db.session.scalar(select(AuditLog)).actor_user_id == auth.ids['auth_admin']
    auth.client.set_cookie("session",captured_cookie)
    assert auth.client.get("/profile").status_code == 302


@pytest.mark.parametrize("username",["auth_teacher","auth_student"])
def test_non_admin_cannot_reset_password_by_get_or_post(auth,username):
    auth.login(username)
    path=f"/admin/users/{auth.ids['auth_admin']}/reset-password"
    assert auth.client.get(path).status_code == 403
    assert auth.client.post(path,data={"csrf_token":auth.token("/profile"), "admin_password":auth.password,
        "new_password":"bad", "confirm_password":"bad"}).status_code == 403


def test_password_changes_require_csrf_and_existing_target(auth):
    auth.login()
    assert auth.client.post("/password/change").status_code == 400
    assert auth.client.post(f"/admin/users/{auth.ids['auth_student']}/reset-password").status_code == 400
    assert auth.client.get("/admin/users/999999/reset-password").status_code == 404


def test_admin_has_usable_username_lookup_for_password_reset(auth):
    auth.login()
    response=auth.client.post("/admin/password-reset", data={"csrf_token":auth.token("/admin/password-reset"), "username":"auth_student"})
    assert response.status_code == 303
    assert response.location == f"/admin/users/{auth.ids['auth_student']}/reset-password"


def test_password_service_owns_no_commit_and_rolls_back_audit_with_change(auth):
    from app.extensions import db
    from app.models import User, AuditLog
    from app.services.password_service import change_own_password
    with auth.app.app_context():
        user=db.session.get(User,auth.ids['auth_admin'])
        original=user.password_hash
        change_own_password(user,auth.password,"temporarily-changed")
        db.session.flush()
        assert db.session.scalar(select(AuditLog)) is not None
        db.session.rollback()
        assert db.session.get(User,user.user_id).password_hash == original
        assert db.session.scalar(select(AuditLog)) is None


def test_password_service_rejects_unusable_actor_or_invalid_new_password(auth):
    from app.extensions import db
    from app.models import User
    from app.services.password_service import change_own_password, reset_user_password
    with auth.app.app_context():
        actor=db.session.get(User,auth.ids['auth_student'])
        for password in ("",None,"a"*1025):
            with pytest.raises(ValueError): change_own_password(actor,auth.password,password)
        with pytest.raises(PermissionError): reset_user_password(actor,auth.ids['auth_admin'],auth.password,"new-value")
        actor.is_active=False
        with pytest.raises(PermissionError): change_own_password(actor,auth.password,"new-value")
