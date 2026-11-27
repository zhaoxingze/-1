"""Audit helpers add immutable snapshots to the caller's transaction."""

import pytest
from sqlalchemy import select


@pytest.mark.parametrize("helper_name, action", [("record_create", "create"), ("record_update", "update"), ("record_archive", "archive"), ("record_status_change", "status_change")])
def test_audit_helpers_record_action_without_commit_or_flush(test_db, monkeypatch, helper_name, action):
    from app.services import audit_service

    def forbidden(*args, **kwargs):
        pytest.fail("audit helpers must not flush or commit")

    monkeypatch.setattr(test_db.session, "flush", forbidden)
    monkeypatch.setattr(test_db.session, "commit", forbidden)
    row = getattr(audit_service, helper_name)("Student", 12, before_data={"status": "enrolled"}, after_data={"status": "suspended"}, request_id="req-1")
    assert row.action == action
    assert row.entity_type == "Student"
    assert row.entity_id == 12
    assert row.actor_user_id is None
    assert row.request_id == "req-1"
    assert row.before_data == {"status": "enrolled"}
    assert row.after_data == {"status": "suspended"}
    assert row in test_db.session.new
    assert row.audit_id is None


def test_audit_cleans_nested_credentials_and_copies_snapshots(test_db):
    from app.services.audit_service import record_update

    before = {"name": "old", "Password_Hash": "never", "nested": {"access_token": "never", "values": [{"api_key": "never", "name": "keep"}, {"cookie": "never", "private_key": "never"}]}}
    after = {"secret": "never", "credential": "never", "authorization": "never", "name": "new"}
    row = record_update("User", 8, before_data=before, after_data=after, session=test_db.session)
    before["nested"]["values"][0]["name"] = "mutated"
    after["name"] = "mutated"
    assert row.before_data == {"name": "old", "nested": {"values": [{"name": "keep"}, {}]}}
    assert row.after_data == {"name": "new"}


@pytest.mark.parametrize("snapshot", [{"nested": {"value": object()}}, {"nested": [float("nan")]}, {"value": float("inf")}, {"value": -float("inf")}])
@pytest.mark.parametrize("field", ["before_data", "after_data"])
def test_audit_rejects_non_json_or_nonfinite_snapshots_before_add(test_db, snapshot, field):
    from app.models import AuditLog
    from app.services.audit_service import record_update

    with pytest.raises(ValueError, match="JSON"):
        record_update("Student", 1, **{field: snapshot})
    assert not any(isinstance(row, AuditLog) for row in test_db.session.new)


@pytest.mark.parametrize("action", ["restore", "delete"])
def test_general_audit_supports_restore_and_delete(test_db, action):
    from app.services.audit_service import record_audit

    row = record_audit("Student", 1, action=action)
    test_db.session.flush()
    assert row.action == action
    assert row.created_at is not None
    assert row.created_at.tzinfo is None


def test_audit_can_rollback_with_actual_business_change(test_db):
    from app.models import Role, AuditLog
    from app.services.audit_service import record_create

    role = Role(name="admin")
    test_db.session.add(role)
    test_db.session.flush()
    record_create("Role", role.role_id)
    test_db.session.flush()
    test_db.session.rollback()
    assert test_db.session.scalar(select(Role)) is None
    assert test_db.session.scalar(select(AuditLog)) is None


def test_archive_helper_does_not_archive_student_or_disable_account(test_db):
    from datetime import date
    from app.models import Role, Student, User
    from app.services.audit_service import record_archive

    student = Student(student_no="S1", name="虚构学生", gender="unspecified", enrollment_date=date(2026, 9, 1))
    actor = User(username="admin", password_hash="hash", role=Role(name="admin"))
    test_db.session.add_all([student, actor])
    test_db.session.flush()
    row = record_archive("Student", student.student_id, actor_user_id=actor.user_id)
    assert row.actor_user_id == actor.user_id
    assert student.is_archived is False
    assert student.status == "enrolled"
    assert actor.is_active is True


@pytest.mark.parametrize("kwargs", [{"entity_type": " ", "entity_id": 1}, {"entity_type": "User", "entity_id": None}, {"entity_type": "User", "entity_id": True}, {"entity_type": "User", "entity_id": 1, "action": "unsupported"}])
def test_invalid_audit_arguments_fail_as_value_error(test_db, kwargs):
    from app.services.audit_service import record_audit

    kwargs.setdefault("action", "create")
    with pytest.raises(ValueError):
        record_audit(**kwargs)
