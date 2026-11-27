from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import AuditLog, Role, User
from archive_support import submit
from stage7_support import actor, create_fields, unmanaged_profiles, user_fields


def test_status_change_revokes_stale_session_after_disable_and_reenable(auth):
    from app.services.user_management_service import set_user_active

    assert auth.login("auth_student").status_code == 303
    original_cookie = auth.client.get_cookie("session")
    with auth.app.app_context():
        admin = actor(auth)
        target = auth.ids["auth_student"]
        set_user_active(admin, target, False)
        db.session.commit()
        assert db.session.get(User, target).student.is_archived is False
    assert auth.client.get("/dashboard/student").status_code == 302
    with auth.app.app_context():
        set_user_active(actor(auth), target, True)
        db.session.commit()
        logs = db.session.scalars(select(AuditLog).order_by(AuditLog.audit_id)).all()
        assert [log.action for log in logs] == ["status_change", "status_change"]
        assert [log.after_data["is_active"] for log in logs] == [False, True]
    auth.client.set_cookie("session", original_cookie.value)
    assert auth.client.get("/dashboard/student").status_code == 302
    assert auth.login("auth_student").status_code == 303
    assert auth.client.get("/dashboard/student").status_code == 200


@pytest.mark.parametrize("change", ["role", "binding"])
def test_reversed_identity_changes_still_revoke_previous_cookie(auth, unmanaged_profiles, change):
    from app.services.user_management_service import update_user

    auth.login("auth_teacher")
    old_cookie = auth.client.get_cookie("session").value
    with auth.app.app_context():
        admin = actor(auth)
        target = actor(auth, "auth_teacher")
        previous_id = target.teacher_id
        changed = {"role": "admin"} if change == "role" else {"role": "teacher", "teacher_id": unmanaged_profiles.teacher}
        update_user(admin, target.user_id, user_fields(username=target.username, **changed))
        db.session.commit()
        identity = target.user_id
    assert auth.client.get("/dashboard/teacher").status_code == 302
    with auth.app.app_context():
        update_user(actor(auth), identity, user_fields(username="auth_teacher", role="teacher", teacher_id=previous_id))
        db.session.commit()
    auth.client.set_cookie("session", old_cookie)
    assert auth.client.get("/dashboard/teacher").status_code == 302


def test_sole_admin_cannot_disable_or_change_self(auth, unmanaged_profiles):
    from app.services.user_management_service import set_user_active, update_user

    with auth.app.app_context():
        admin = actor(auth)
        for operation in (
            lambda: set_user_active(admin, admin.user_id, False),
            lambda: update_user(admin, admin.user_id, user_fields(username=admin.username, role="teacher",
                                                                  teacher_id=unmanaged_profiles.teacher)),
            lambda: update_user(admin, admin.user_id, user_fields(username=admin.username,
                                                                  student_id=unmanaged_profiles.student)),
        ):
            with pytest.raises((ValueError, PermissionError)):
                operation()
            db.session.rollback()
        assert admin.is_active and admin.role.name == "admin"


def test_competing_admin_actions_leave_one_active(auth):
    from app.services.user_management_service import create_user, set_user_active

    with auth.app.app_context():
        admin = actor(auth)
        other = create_user(admin, create_fields(username="peer_admin"))
        db.session.commit()
        ids = admin.user_id, other.user_id
    ready = Barrier(2, timeout=10)

    def attempt(actor_id, target_id):
        with auth.app.app_context():
            operator = db.session.get(User, actor_id)
            assert operator.is_active is True and operator.role.name == "admin"
            ready.wait()
            try:
                set_user_active(operator, target_id, False)
                db.session.commit()
            except PermissionError:
                db.session.rollback()
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, ids[0], ids[1]), pool.submit(attempt, ids[1], ids[0])]
        assert sorted(f.result(timeout=15) for f in futures) == [False, True]
    with auth.app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User).join(Role)
                                 .where(Role.name == "admin", User.is_active.is_(True))) == 1


@pytest.mark.parametrize("username", ["auth_teacher", "auth_student"])
def test_account_routes_deny_nonadmins(auth, username):
    auth.login(username)
    for path in ("/admin/users", "/admin/users/new", f"/admin/users/{auth.ids['auth_admin']}",
                 f"/admin/users/{auth.ids['auth_admin']}/edit"):
        assert auth.client.get(path).status_code == 403
    assert auth.client.post("/admin/users/new", data={**create_fields(), "csrf_token": auth.token("/profile")}).status_code == 403


def test_account_post_needs_csrf_and_rejects_raw_role_id(auth):
    auth.login()
    path = "/admin/users/new"
    assert auth.client.post(path, data=create_fields()).status_code == 400
    assert submit(auth, path, {**create_fields(), "role_id": 17}).status_code == 400
