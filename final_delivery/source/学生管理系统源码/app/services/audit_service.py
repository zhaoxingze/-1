"""Append audit records within the business transaction, without committing."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.extensions import db

if TYPE_CHECKING:
    from app.models import AuditLog


_ACTIONS = frozenset({"create", "update", "archive", "restore", "status_change", "delete"})


def record_audit(entity_type, entity_id, *, action, actor_user_id=None, before_data=None, after_data=None, request_id=None, session=None) -> AuditLog:
    """Add one sanitized audit snapshot; do not mutate the business entity."""
    from app.models import AuditLog
    from app.models.security import sanitize_snapshot

    if not isinstance(entity_type, str) or not entity_type.strip() or len(entity_type) > 80:
        raise ValueError("entity_type must be nonempty and at most 80 characters")
    if isinstance(entity_id, bool) or not isinstance(entity_id, int):
        raise ValueError("entity_id must be an integer")
    if action not in _ACTIONS:
        raise ValueError("Unsupported audit action")
    if actor_user_id is not None and (isinstance(actor_user_id, bool) or not isinstance(actor_user_id, int)):
        raise ValueError("actor_user_id must be an integer or None")
    if request_id is not None and (not isinstance(request_id, str) or len(request_id) > 100):
        raise ValueError("request_id must be a string of at most 100 characters")
    try:
        before = json.loads(json.dumps(sanitize_snapshot(before_data), allow_nan=False))
        after = json.loads(json.dumps(sanitize_snapshot(after_data), allow_nan=False))
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("Audit snapshots must be JSON serializable") from exc
    row = AuditLog(entity_type=entity_type, entity_id=entity_id, action=action, actor_user_id=actor_user_id, before_data=before, after_data=after, request_id=request_id)
    (db.session if session is None else session).add(row)
    return row


def record_create(entity_type, entity_id, *, actor_user_id=None, before_data=None, after_data=None, request_id=None, session=None) -> AuditLog:
    return record_audit(entity_type, entity_id, action="create", actor_user_id=actor_user_id, before_data=before_data, after_data=after_data, request_id=request_id, session=session)


def record_update(entity_type, entity_id, *, actor_user_id=None, before_data=None, after_data=None, request_id=None, session=None) -> AuditLog:
    return record_audit(entity_type, entity_id, action="update", actor_user_id=actor_user_id, before_data=before_data, after_data=after_data, request_id=request_id, session=session)


def record_archive(entity_type, entity_id, *, actor_user_id=None, before_data=None, after_data=None, request_id=None, session=None) -> AuditLog:
    return record_audit(entity_type, entity_id, action="archive", actor_user_id=actor_user_id, before_data=before_data, after_data=after_data, request_id=request_id, session=session)


def record_status_change(entity_type, entity_id, *, actor_user_id=None, before_data=None, after_data=None, request_id=None, session=None) -> AuditLog:
    return record_audit(entity_type, entity_id, action="status_change", actor_user_id=actor_user_id, before_data=before_data, after_data=after_data, request_id=request_id, session=session)
