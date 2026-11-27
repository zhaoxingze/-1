import pytest
from sqlalchemy import select, text
from werkzeug.datastructures import MultiDict

from teacher_scope_support import scoped_teacher


def _submit(auth, path, **data):
    return auth.client.post(path, data={"csrf_token": auth.token(path), **data})


def test_teacher_updates_only_contact_and_appends_audit(scoped_teacher):
    from app.extensions import db
    from app.models import AuditLog, Student

    auth, ids = scoped_teacher
    response = _submit(auth, f"/teacher/students/{ids.own}/contact", phone="000-4991", address="更新后的虚构地址")
    assert response.status_code == 303
    with auth.app.app_context():
        student = db.session.get(Student, ids.own)
        assert (student.phone, student.address) == ("000-4991", "更新后的虚构地址")
        log = db.session.scalar(select(AuditLog))
        assert (log.actor_user_id, log.entity_type, log.entity_id, log.action) == (
            auth.ids["auth_teacher"], "Student", ids.own, "update",
        )
        assert log.before_data == {"phone": "000-4001", "address": "虚构本班地址"}
        assert log.after_data == {"phone": "000-4991", "address": "更新后的虚构地址"}
        assert log.created_at is not None


@pytest.mark.parametrize("field", ["student_no", "status", "is_archived", "is_active", "class_id", "teacher_id", "role_id", "actor_user_id", "name", "student_id"])
def test_rejects_unauthorized_form_fields(scoped_teacher, field):
    from app.extensions import db
    from app.models import AuditLog, Student

    auth, ids = scoped_teacher
    response = _submit(auth, f"/teacher/students/{ids.own}/contact", phone="000-4999", **{field: "1"})
    assert response.status_code == 400
    with auth.app.app_context():
        student = db.session.get(Student, ids.own)
        assert (student.student_no, student.phone, student.status, student.is_archived) == (
            "AUTH-S1", "000-4001", "enrolled", False,
        )
        assert db.session.scalar(select(AuditLog)) is None


def test_audit_insert_failure_rolls_back_the_contact_edit(scoped_teacher):
    from app.extensions import db
    from app.models import AuditLog, Student

    auth, ids = scoped_teacher
    with auth.app.app_context():
        db.session.execute(text("CREATE TRIGGER reject_4b_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'fixture-only error'); END"))
        db.session.commit()
    response = _submit(auth, f"/teacher/students/{ids.own}/contact", phone="000-4999")
    assert response.status_code == 409
    assert "fixture-only error" not in response.text
    with auth.app.app_context():
        assert db.session.get(Student, ids.own).phone == "000-4001"
        assert db.session.scalar(select(AuditLog)) is None


def test_rejects_duplicate_fields_and_missing_csrf(scoped_teacher):
    auth, ids = scoped_teacher
    path = f"/teacher/students/{ids.own}/contact"
    assert auth.client.post(path, data={"phone": "000-4999"}).status_code == 400
    data = MultiDict([("csrf_token", auth.token(path)), ("phone", "000-4998"), ("phone", "000-4999")])
    assert auth.client.post(path, data=data).status_code == 400


def test_post_rechecks_scope_after_student_transfer(scoped_teacher):
    from app.extensions import db
    from app.models import Student

    auth, ids = scoped_teacher
    path = f"/teacher/students/{ids.own}/contact"
    csrf_token = auth.token(path)
    with auth.app.app_context():
        db.session.get(Student, ids.own).class_id = ids.other_class
        db.session.commit()
    assert auth.client.post(path, data={"csrf_token": csrf_token, "phone": "000-4999"}).status_code == 403


def test_service_whitelist_and_fresh_scope_in_an_independent_session(scoped_teacher):
    from sqlalchemy.orm import Session
    from app.extensions import db
    from app.models import Student, User
    from app.services.teacher_student_service import update_student_contact
    from unittest.mock import patch

    auth, ids = scoped_teacher
    with auth.app.app_context(), Session(db.engine) as first, Session(db.engine) as second:
        actor = first.get(User, auth.ids["auth_teacher"])
        cached = first.get(Student, ids.own)
        assert cached.class_id == ids.own_class
        with patch.object(db, "session", first):
            with pytest.raises(ValueError):
                update_student_contact(actor, ids.own, {"student_no": "DENIED"})
        second.get(Student, ids.own).class_id = ids.other_class
        second.commit()
        with patch.object(db, "session", first):
            with pytest.raises(PermissionError):
                update_student_contact(actor, ids.own, {"phone": "000-4999"})
            first.rollback()
        assert second.get(Student, ids.own).phone == "000-4001"
