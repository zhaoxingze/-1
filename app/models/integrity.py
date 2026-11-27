"""ORM validation and SQLite guards shared with the frozen initial migration.

The migration copies these SQL strings so its history remains independent of
future application code. Metadata creation installs the same guards for tests.
"""

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from app.extensions import db
from .audit_log import AuditLog
from .notification_log import NotificationLog
from .parent import Parent
from .parent_contact import ParentContactLog
from .role import Role
from .security import sanitize_snapshot
from .student import Student
from .user import User


SQLITE_TRIGGERS = {
    "audit_logs_no_update": """
CREATE TRIGGER IF NOT EXISTS audit_logs_no_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit logs are append-only');
END
""",
    "audit_logs_no_delete": """
CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit logs are append-only');
END
""",
    "parent_contacts_parent_insert": """
CREATE TRIGGER IF NOT EXISTS parent_contacts_parent_insert
BEFORE INSERT ON parent_contact_logs
WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND student_id = NEW.student_id
)
BEGIN
    SELECT RAISE(ABORT, 'contact parent must belong to the same student');
END
""",
    "parent_contacts_parent_update": """
CREATE TRIGGER IF NOT EXISTS parent_contacts_parent_update
BEFORE UPDATE OF parent_id, student_id ON parent_contact_logs
WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND student_id = NEW.student_id
)
BEGIN
    SELECT RAISE(ABORT, 'contact parent must belong to the same student');
END
""",
    "notifications_parent_insert": """
CREATE TRIGGER IF NOT EXISTS notifications_parent_insert
BEFORE INSERT ON notification_logs
WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND student_id = NEW.student_id
)
BEGIN
    SELECT RAISE(ABORT, 'notification parent must belong to the same student');
END
""",
    "notifications_parent_update": """
CREATE TRIGGER IF NOT EXISTS notifications_parent_update
BEFORE UPDATE OF parent_id, student_id ON notification_logs
WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND student_id = NEW.student_id
)
BEGIN
    SELECT RAISE(ABORT, 'notification parent must belong to the same student');
END
""",
    "parents_preserve_history_owner": """
CREATE TRIGGER IF NOT EXISTS parents_preserve_history_owner
BEFORE UPDATE OF student_id ON parents
WHEN EXISTS (
    SELECT 1 FROM parent_contact_logs
    WHERE parent_id = OLD.parent_id AND student_id != NEW.student_id
) OR EXISTS (
    SELECT 1 FROM notification_logs
    WHERE parent_id = OLD.parent_id AND student_id != NEW.student_id
)
BEGIN
    SELECT RAISE(ABORT, 'parent reassignment conflicts with existing history');
END
""",
}


@event.listens_for(db.metadata, "after_create")
def _install_sqlite_guards(metadata, connection, **kwargs):
    if connection.dialect.name == "sqlite":
        for statement in SQLITE_TRIGGERS.values():
            connection.exec_driver_sql(statement)


def _resolve_related(owner, relation_name, foreign_key_name, model, session):
    """Resolve edits without trusting stale FKs or loading with autoflush."""
    state = inspect(owner)
    relation_changed = state.attrs[relation_name].history.has_changes()
    foreign_key_changed = state.attrs[foreign_key_name].history.has_changes()
    foreign_key = getattr(owner, foreign_key_name)
    if relation_changed:
        related = getattr(owner, relation_name)
        if foreign_key_changed and related is not None and foreign_key is not None:
            primary_key = inspect(model).primary_key[0].key
            if getattr(related, primary_key) != foreign_key:
                raise ValueError(f"Conflicting {relation_name} and {foreign_key_name}")
    elif foreign_key is not None:
        primary_key = inspect(model).primary_key[0].key
        related = next((item for item in session.new if isinstance(item, model) and getattr(item, primary_key) == foreign_key), None)
        if related is None:
            related = session.get(model, foreign_key)
    elif foreign_key_changed:
        related = None
    else:
        related = getattr(owner, relation_name)
    if related is not None and (related in session.deleted or inspect(related).deleted):
        raise ValueError(f"{relation_name} references a deleted record")
    if related is None and foreign_key is not None and not relation_changed:
        raise ValueError(f"{foreign_key_name} references a missing record")
    return related


def _validate_contact_target(record, session):
    from app.services.data_validation_service import validate_parent_student_binding

    student = _resolve_related(record, "student", "student_id", Student, session)
    parent = _resolve_related(record, "parent", "parent_id", Parent, session)
    if student is None:
        raise ValueError("A contact or notification requires a student")
    if parent is not None:
        parent_student = _resolve_related(parent, "student", "student_id", Student, session)
        if parent_student is not student:
            raise ValueError("Parent must belong to the same student")
    elif isinstance(record, ParentContactLog):
        name = record.contact_person_name
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A contact without a parent requires contact_person_name")
    # IDs are not available yet for an all-new relationship graph. Its object
    # identity check above is equivalent; normal stored identities use Service.
    if student.student_id is not None and (parent is None or parent.parent_id is not None):
        validate_parent_student_binding(student.student_id, parent.parent_id if parent else None, session=session)


@event.listens_for(Session, "before_flush")
def _validate_domain_changes(session, flush_context, instances):
    from app.services.data_validation_service import validate_user_profile_binding

    with session.no_autoflush:
        for value in session.deleted:
            if isinstance(value, AuditLog):
                raise ValueError("Audit logs are append-only and cannot be deleted")
        for value in session.dirty:
            if isinstance(value, AuditLog) and session.is_modified(value, include_collections=False):
                raise ValueError("Audit logs are append-only and cannot be modified")
        for value in list(session.new) + list(session.dirty):
            if isinstance(value, AuditLog) and value in session.new:
                value.before_data = sanitize_snapshot(value.before_data)
                value.after_data = sanitize_snapshot(value.after_data)
            elif isinstance(value, User) and value not in session.deleted:
                validate_user_profile_binding(value, session=session)
            elif isinstance(value, (ParentContactLog, NotificationLog)) and value not in session.deleted:
                _validate_contact_target(value, session)
            elif isinstance(value, Role) and inspect(value).attrs.name.history.has_changes() and value.role_id is not None:
                for user in session.scalars(select(User).where(User.role_id == value.role_id)):
                    if user not in session.deleted:
                        validate_user_profile_binding(user, session=session)
