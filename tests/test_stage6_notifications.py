import socket

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import NotificationLog, Parent
from archive_support import submit
from student_records_support import NOTICE, actor, scoped_teacher, student_records


@pytest.mark.parametrize("channel", ["sms", "email"])
def test_notification_uses_existing_simulation_and_detaches_recipient(student_records, monkeypatch, channel):
    from app.services import notification_service
    from app.services.parent_contact_service import simulate_notification

    def forbidden(*args, **kwargs):
        pytest.fail("Simulation must not contact a provider")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    original = notification_service.create_simulated_notification
    calls = []

    def tracked(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(notification_service, "create_simulated_notification", tracked)
    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        row = simulate_notification(actor(auth), ids.own, {**NOTICE, "parent_id": ids.parent, "channel": channel})
        db.session.commit()
        parent = db.session.get(Parent, ids.parent)
        parent.phone = "000-4099"
        db.session.commit()
        assert calls == [True] and row.status == "simulated"
        assert row.recipient_snapshot == {"name": "本班虚构家长", "phone": "000-4011", "email": "own@example.invalid"}


@pytest.mark.parametrize("change", [{"channel": "push"}, {"parent_id": "other"}, {"channel": "email", "recipient_address": "invalid"}])
def test_simulation_rejects_bad_channels_bindings_or_addresses(student_records, change):
    from app.services.parent_contact_service import simulate_notification

    auth, ids = student_records.auth, student_records.ids
    if change.get("parent_id") == "other":
        change = {"parent_id": ids.other_parent}
    with auth.app.app_context(), pytest.raises(ValueError):
        simulate_notification(actor(auth), ids.own, {**NOTICE, "recipient_name": "临时联系",
                                                     "recipient_address": "000-5555", **change})


def test_notification_route_explicit_simulation(student_records):
    auth, ids = student_records.auth, student_records.ids
    path = "/records/notifications/new"
    assert auth.client.get(path).status_code == 200
    with auth.app.app_context():
        assert db.session.scalar(select(NotificationLog)) is None
    response = submit(auth, path, {**NOTICE, "student_id": ids.own, "parent_id": ids.parent})
    assert response.status_code == 303
    detail = auth.client.get(response.location)
    assert "模拟通知，未实际发送" in detail.text and "000-4011" in detail.text


def test_explicit_recipient_uses_only_selected_channel(student_records):
    from app.services.parent_contact_service import simulate_notification

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        row = simulate_notification(actor(auth), ids.own, {**NOTICE, "channel": "email", "recipient_name": "临时联系人",
                                                          "recipient_address": "example@example.invalid"})
        assert row.parent_id is None and row.recipient_snapshot == {
            "name": "临时联系人", "email": "example@example.invalid",
        }
