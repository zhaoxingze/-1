"""Notification preparation is local-only and snapshots recipients once."""

from datetime import date
import socket

import pytest
from sqlalchemy import select


def _targets(test_db):
    from app.models import Role, User, Student, Parent

    first = Student(student_no="S1", name="虚构学生甲", gender="unspecified", enrollment_date=date(2026, 9, 1))
    second = Student(student_no="S2", name="虚构学生乙", gender="unspecified", enrollment_date=date(2026, 9, 1))
    actor = User(username="admin", password_hash="hash", role=Role(name="admin"))
    parent = Parent(student=first, name="虚构家长", relationship="guardian", phone="000-100", email="guardian@example.invalid")
    test_db.session.add_all([first, second, actor, parent])
    test_db.session.flush()
    return first, second, actor, parent


def test_notification_target_checks_parent_and_student(test_db):
    from app.services.notification_service import validate_notification_target

    first, second, _, parent = _targets(test_db)
    assert validate_notification_target(first.student_id, parent.parent_id) is parent
    assert validate_notification_target(first.student_id) is None
    for sid, pid in [(second.student_id, parent.parent_id), (99999, None), (first.student_id, 99999)]:
        with pytest.raises(ValueError):
            validate_notification_target(sid, pid, session=test_db.session)


@pytest.mark.parametrize("channel", ["sms", "email"])
def test_simulation_copies_parent_recipient_and_does_no_network(test_db, monkeypatch, channel):
    from app.services.notification_service import create_simulated_notification

    first, _, actor, parent = _targets(test_db)

    def forbidden(*args, **kwargs):
        pytest.fail("simulation must not send network requests or commit/flush")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(test_db.session, "commit", forbidden)
    monkeypatch.setattr(test_db.session, "flush", forbidden)
    row = create_simulated_notification(first.student_id, channel, "模拟通知", created_by=actor.user_id, parent_id=parent.parent_id)
    assert row.status == "simulated"
    assert row.channel == channel
    assert row.recipient_snapshot == {"name": parent.name, "phone": parent.phone, "email": parent.email}
    assert row in test_db.session.new
    parent.phone = "000-200"
    assert row.recipient_snapshot["phone"] == "000-100"


def test_no_parent_requires_explicit_nonempty_snapshot_and_copies_it(test_db):
    from app.services.notification_service import create_simulated_notification

    first, _, actor, _ = _targets(test_db)
    for snapshot in [None, {}, "", {"name": " "}]:
        with pytest.raises(ValueError):
            create_simulated_notification(first.student_id, "sms", "模拟通知", created_by=actor.user_id, recipient_snapshot=snapshot)
    snapshot = {"name": "临时监护人", "phone": "000-300", "details": {"source": "manual"}}
    row = create_simulated_notification(first.student_id, "sms", "模拟通知", created_by=actor.user_id, recipient_snapshot=snapshot)
    snapshot["details"]["source"] = "mutated"
    assert row.recipient_snapshot["details"]["source"] == "manual"


@pytest.mark.parametrize("channel, content", [("push", "message"), ("sms", " "), (None, "message"), ("email", None)])
def test_notification_rejects_invalid_channel_or_content(test_db, channel, content):
    from app.services.notification_service import create_simulated_notification

    first, _, actor, parent = _targets(test_db)
    with pytest.raises(ValueError):
        create_simulated_notification(first.student_id, channel, content, created_by=actor.user_id, parent_id=parent.parent_id)


def test_notification_rejects_missing_deleted_actor_and_wrong_parent(test_db):
    from app.services.notification_service import create_simulated_notification

    first, second, actor, parent = _targets(test_db)
    with pytest.raises(ValueError):
        create_simulated_notification(first.student_id, "sms", "message", created_by=99999, parent_id=parent.parent_id)
    with pytest.raises(ValueError):
        create_simulated_notification(second.student_id, "sms", "message", created_by=actor.user_id, parent_id=parent.parent_id)
    test_db.session.delete(actor)
    with pytest.raises(ValueError):
        create_simulated_notification(first.student_id, "sms", "message", created_by=actor.user_id, parent_id=parent.parent_id)


def test_notification_is_rollbackable(test_db):
    from app.models import NotificationLog
    from app.services.notification_service import create_simulated_notification

    first, _, actor, parent = _targets(test_db)
    create_simulated_notification(first.student_id, "sms", "message", created_by=actor.user_id, parent_id=parent.parent_id, session=test_db.session)
    test_db.session.flush()
    test_db.session.rollback()
    assert test_db.session.scalar(select(NotificationLog)) is None
