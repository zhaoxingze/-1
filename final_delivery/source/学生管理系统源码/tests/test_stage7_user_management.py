import pytest
from sqlalchemy import select
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import AuditLog, User
from archive_support import submit
from stage7_support import NEW_PASSWORD, actor, create_fields, unmanaged_profiles, user_fields


@pytest.mark.parametrize("role", ["admin", "teacher", "student"])
def test_create_users_hashes_password_and_validates_real_profiles(auth, unmanaged_profiles, role):
    from app.services.user_management_service import create_user

    with auth.app.app_context():
        bindings = {"teacher_id": unmanaged_profiles.teacher} if role == "teacher" else {}
        if role == "student":
            bindings = {"student_id": unmanaged_profiles.student}
        account = create_user(actor(auth), create_fields(role=role, **bindings))
        db.session.commit()
        assert account.role.name == role and account.is_active is True
        assert account.password_hash != NEW_PASSWORD and check_password_hash(account.password_hash, NEW_PASSWORD)
        audit = db.session.scalar(select(AuditLog))
        assert audit.action == "create" and audit.entity_id == account.user_id and audit.actor_user_id == auth.ids["auth_admin"]
        assert set(audit.after_data) == {"username", "role", "student_id", "teacher_id", "is_active"}


@pytest.mark.parametrize("case", ["duplicate", "empty", "length", "confirm", "role_id", "unknown_role",
                                  "admin_binding", "wrong_teacher", "wrong_student", "missing_teacher", "duplicate_teacher", "duplicate_student"])
def test_rejects_invalid_account_inputs(auth, unmanaged_profiles, case):
    from app.services.user_management_service import create_user

    with auth.app.app_context():
        admin = actor(auth)
        teacher_id = actor(auth, "auth_teacher").teacher_id
        profiles = unmanaged_profiles
        invalid = {
            "duplicate": {"username": "auth_admin"}, "empty": {"username": " "}, "length": {"username": "x" * 51},
            "confirm": {"confirm_password": "different"}, "role_id": {"role_id": admin.role_id},
            "unknown_role": {"role": "owner"}, "admin_binding": {"teacher_id": profiles.teacher},
            "wrong_teacher": {"role": "teacher", "student_id": profiles.student},
            "wrong_student": {"role": "student", "teacher_id": profiles.teacher},
            "missing_teacher": {"role": "teacher", "teacher_id": 999999},
            "duplicate_teacher": {"role": "teacher", "teacher_id": teacher_id},
            "duplicate_student": {"role": "student", "student_id": auth.student_ids[0]},
        }[case]
        with pytest.raises(ValueError):
            create_user(admin, {**create_fields(), **invalid})
        assert db.session.scalar(select(User.user_id).where(User.username == "new_account")) is None


def test_user_list_filters_and_account_detail_show_password_reset_link(auth):
    auth.login()
    path = "/admin/users?role=student&active=1&per_page=1"
    page = auth.client.get(path)
    assert page.status_code == 200 and "共 2 条" in page.text and "下一页" in page.text
    assert auth.client.get(path + "&page=2").status_code == 200
    filtered = auth.client.get("/admin/users?q=disabled&active=0")
    assert filtered.status_code == 200 and "disabled" in filtered.text and "共 1 条" in filtered.text
    identity = auth.ids["auth_student"]
    detail = auth.client.get(f"/admin/users/{identity}")
    assert f'href="/admin/users/{identity}/reset-password"' in detail.text
    assert "scrypt:" not in detail.text


def test_account_forms_submit_and_atomic_audit_failure(auth):
    from sqlalchemy import text

    auth.login()
    fields = create_fields()
    created = submit(auth, "/admin/users/new", fields)
    assert created.status_code == 303
    path = created.location + "/edit"
    with auth.app.app_context():
        db.session.execute(text("CREATE TRIGGER reject_user_audit BEFORE INSERT ON audit_logs "
                                "BEGIN SELECT RAISE(ABORT, 'test-only failure'); END"))
        db.session.commit()
    assert submit(auth, path, user_fields(username="renamed")).status_code == 409
    with auth.app.app_context():
        account = db.session.get(User, int(created.location.rsplit("/", 1)[1]))
        assert account.username == fields["username"]
        assert len(db.session.scalars(select(AuditLog)).all()) == 1
