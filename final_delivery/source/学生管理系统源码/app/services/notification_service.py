"""Local notification simulation. This module never contacts a provider."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.extensions import db
from app.services.data_validation_service import _find_existing, validate_parent_student_binding

if TYPE_CHECKING:
    from app.models import NotificationLog, Parent


def validate_notification_target(student_id, parent_id=None, *, session=None) -> Parent | None:
    return validate_parent_student_binding(student_id, parent_id, session=session)


def _has_recipient_value(value):
    if isinstance(value, dict):
        return any(_has_recipient_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_recipient_value(item) for item in value)
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def create_simulated_notification(student_id, channel, content, *, created_by, parent_id=None, recipient_snapshot=None, session=None) -> NotificationLog:
    """Add a simulated notification and a detached JSON recipient snapshot."""
    from app.models import NotificationLog, User

    session = db.session if session is None else session
    if channel not in {"sms", "email"}:
        raise ValueError("Notification channel must be sms or email")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Notification content must be nonempty")
    with session.no_autoflush:
        parent = validate_notification_target(student_id, parent_id, session=session)
        if _find_existing(User, created_by, session) is None:
            raise ValueError("Notification creator does not exist")
        if recipient_snapshot is None and parent is not None:
            recipient_snapshot = {"name": parent.name, "phone": parent.phone, "email": parent.email}
        if not isinstance(recipient_snapshot, dict) or not _has_recipient_value(recipient_snapshot):
            raise ValueError("A nonempty recipient snapshot is required")
        try:
            snapshot = json.loads(json.dumps(recipient_snapshot, allow_nan=False))
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise ValueError("Recipient snapshot must be JSON serializable") from exc
        row = NotificationLog(student_id=student_id, parent_id=parent_id, channel=channel, recipient_snapshot=snapshot, content=content, status="simulated", created_by=created_by)
        session.add(row)
        return row
