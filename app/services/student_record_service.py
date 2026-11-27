"""Shared student-scoped queries, validation and audit for the record modules."""

from datetime import datetime, time, timezone

from sqlalchemy import inspect, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Parent, SchoolClass, Student
from .archive_common import ArchiveValidationError, begin_archive_write, date_value, snapshot
from .audit_service import record_audit
from .permission_service import student_record_access, valid_scope_id


def begin_record_write(actor, action):
    student_record_access(actor, action)
    begin_archive_write()
    return student_record_access(actor, action)


def require_student(scope, student_id):
    if valid_scope_id(student_id):
        row = db.session.scalar(select(Student).where(Student.student_id == student_id, scope.students())
                                .execution_options(populate_existing=True))
        if row is not None:
            return row
    if scope.role == "admin":
        raise LookupError("Student does not exist")
    raise PermissionError("Student outside record scope")


def require_parent(scope, parent_id):
    if valid_scope_id(parent_id):
        row = db.session.scalar(select(Parent).join(Student).where(Parent.parent_id == parent_id, scope.students())
                                .execution_options(populate_existing=True))
        if row is not None:
            return row
    if scope.role == "admin":
        raise LookupError("Parent does not exist")
    raise PermissionError("Parent outside record scope")


def record_options(actor, action, *, include_classes=False, include_parents=False, class_id=None):
    scope = student_record_access(actor, action)
    student_query = select(Student.student_id, Student.student_no, Student.name).where(scope.students())
    if class_id is not None:
        student_query = student_query.where(Student.class_id == class_id)
    students = db.session.execute(student_query.order_by(Student.student_no))
    options = {"students": [(key, f"{number} · {name}") for key, number, name in students]}
    if include_classes:
        classes = db.session.execute(select(SchoolClass.class_id, SchoolClass.grade, SchoolClass.class_name)
                                     .where(scope.classes()).order_by(SchoolClass.grade, SchoolClass.class_name))
        options["classes"] = [(key, f"{grade} · {name}") for key, grade, name in classes]
    if include_parents:
        parents = db.session.execute(select(Parent.parent_id, Student.student_no, Parent.name).join(Student)
                                     .where(scope.students()).order_by(Student.student_no, Parent.parent_id))
        options["parents"] = [(key, f"{number} · {name}") for key, number, name in parents]
    return options


def record_filters(scope, column, *, student_id=None, class_id=None, start=None, end=None, utc=False):
    conditions = [scope.students()]
    if student_id is not None:
        require_student(scope, student_id)
        conditions.append(Student.student_id == student_id)
    if class_id is not None:
        exists = valid_scope_id(class_id) and db.session.scalar(select(SchoolClass.class_id).where(
            SchoolClass.class_id == class_id, scope.classes()
        ))
        if not exists:
            if scope.role == "admin":
                raise LookupError("Class does not exist")
            raise PermissionError("Class outside record scope")
        conditions.append(Student.class_id == class_id)
    left, right = date_value({"start": start}, "start"), date_value({"end": end}, "end")
    if left is not None and right is not None and left > right:
        raise ArchiveValidationError("end", "结束日期不能早于起始日期。")
    if left is not None:
        conditions.append(column >= (datetime.combine(left, time.min) if utc else left))
    if right is not None:
        conditions.append(column <= (datetime.combine(right, time.max) if utc else right))
    return conditions


def scoped_record(scope, model, record_id, *, fresh=False):
    if valid_scope_id(record_id):
        key = inspect(model).primary_key[0]
        statement = select(model).join(Student).where(key == record_id, scope.students())
        row = db.session.scalar(statement.options(selectinload(model.student)).execution_options(populate_existing=fresh))
        if row is not None:
            return row
    if scope.role == "admin":
        raise LookupError("Record does not exist")
    raise PermissionError("Record outside student scope")


def enum_value(data, field, labels):
    value = data.get(field)
    if not isinstance(value, str) or value not in labels:
        raise ArchiveValidationError(field, "请选择有效选项。")
    return value


def long_text(data, field, *, required=False):
    value = data.get(field)
    if not required and value in ("", None):
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ArchiveValidationError(field, "请输入有效内容。")
    return value


def utc_datetime(data, field):
    value = data.get(field)
    if isinstance(value, datetime):
        try:
            return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
        except (OverflowError, ValueError):
            pass
    raise ArchiveValidationError(field, "请输入有效的 UTC 联系时间。")


def save_record(actor, row, values, visible_fields, *, creating=False):
    """Flush business state and append only permitted metadata to the same session."""
    before = None if creating else snapshot(row, visible_fields)
    changed = [field for field, value in values.items() if creating or getattr(row, field) != value]
    for field, value in values.items():
        setattr(row, field, value)
    if creating:
        db.session.add(row)
    db.session.flush()
    after = snapshot(row, visible_fields)
    after["changed_fields"] = sorted(changed)
    key = inspect(type(row)).primary_key[0]
    record_audit(type(row).__name__, getattr(row, key.key), actor_user_id=actor.user_id,
                 action="create" if creating else "update", before_data=before, after_data=after)
    return row
