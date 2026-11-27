"""Small integrity validators; transaction ownership remains with callers."""

from __future__ import annotations

from decimal import Decimal
import math
from numbers import Real
from typing import TYPE_CHECKING

from sqlalchemy import inspect

from app.extensions import db

if TYPE_CHECKING:
    from app.models import Parent


def _session(session):
    return db.session if session is None else session


def _is_deleted(value, session):
    return value in session.deleted or inspect(value).deleted


def _find_existing(model, identity, session):
    """Resolve persisted or pending IDs without flushing unrelated changes."""
    if identity is None or isinstance(identity, bool) or not isinstance(identity, int):
        return None
    primary_key = inspect(model).primary_key[0].key
    for value in session.new:
        if isinstance(value, model) and getattr(value, primary_key) == identity:
            return None if _is_deleted(value, session) else value
    value = session.get(model, identity)
    return value if value is not None and not _is_deleted(value, session) else None


def _resolve_binding(owner, relationship_name, foreign_key_name, model, session):
    """Respect an explicitly edited FK over a stale loaded relationship.

    SQLAlchemy does not synchronize the FK for a new relationship graph until
    flush. Relationship history therefore carries newly assigned objects while
    FK history carries direct edits to previously loaded objects.
    """
    state = inspect(owner)
    foreign_key = getattr(owner, foreign_key_name)
    foreign_key_changed = state.attrs[foreign_key_name].history.has_changes()
    relationship_changed = state.attrs[relationship_name].history.has_changes()
    if foreign_key_changed and not relationship_changed:
        if foreign_key is None:
            return None
        value = _find_existing(model, foreign_key, session)
        if value is None:
            raise ValueError(f"{foreign_key_name} must reference an existing record")
        return value
    related = getattr(owner, relationship_name)
    if related is not None:
        if not isinstance(related, model) or _is_deleted(related, session):
            raise ValueError(f"{relationship_name} must reference an existing record")
        primary_key = inspect(model).primary_key[0].key
        related_id = getattr(related, primary_key)
        if foreign_key_changed and foreign_key is not None and related_id != foreign_key:
            raise ValueError(f"{relationship_name} conflicts with {foreign_key_name}")
        if related_id is not None and _find_existing(model, related_id, session) is None:
            raise ValueError(f"{relationship_name} must reference an existing record")
        return related
    if relationship_changed:
        return None
    if foreign_key is None:
        return None
    value = _find_existing(model, foreign_key, session)
    if value is None:
        raise ValueError(f"{foreign_key_name} must reference an existing record")
    return value


def validate_user_profile_binding(user, *, session=None) -> None:
    """Validate a user's role by name and the corresponding real profile."""
    from app.models import Role, Student, Teacher

    session = _session(session)
    with session.no_autoflush:
        role = _resolve_binding(user, "role", "role_id", Role, session)
        student = _resolve_binding(user, "student", "student_id", Student, session)
        teacher = _resolve_binding(user, "teacher", "teacher_id", Teacher, session)
        if role is None:
            raise ValueError("A user requires an existing role")
        expected = {"admin": (False, False), "student": (True, False), "teacher": (False, True)}
        if role.name not in expected:
            raise ValueError("Unknown user role")
        if (student is not None, teacher is not None) != expected[role.name]:
            raise ValueError("User role and student/teacher profile binding do not match")


def validate_parent_student_binding(student_id, parent_id, *, session=None) -> Parent | None:
    """Return the matching parent, or None for an existing student alone."""
    from app.models import Parent, Student

    session = _session(session)
    with session.no_autoflush:
        student = _find_existing(Student, student_id, session)
        if student is None:
            raise ValueError("Student does not exist")
        if parent_id is None:
            return None
        parent = _find_existing(Parent, parent_id, session)
        if parent is None:
            raise ValueError("Parent does not exist")
        owner = _resolve_binding(parent, "student", "student_id", Student, session)
        if owner is not student:
            raise ValueError("Parent does not belong to the given student")
        return parent


def validate_score_value(value, *, allow_none=True) -> float | None:
    """Check one score only; this does not decide submission or total policy."""
    if value is None:
        if allow_none:
            return None
        raise ValueError("Score is required")
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise ValueError("Score must be a real number")
    try:
        result = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("Score must be a finite real number") from exc
    if not math.isfinite(result) or not 0 <= result <= 100:
        raise ValueError("Score must be finite and between 0 and 100")
    return result
