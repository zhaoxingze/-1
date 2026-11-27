"""Scoped parent-contact history and audited simulation through the existing service."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import NotificationLog, Parent, ParentContactLog, Student
from . import notification_service
from .archive_common import ArchiveValidationError, check_fields, email_value, optional_relation, pagination, text_value
from .permission_service import (
    NOTIFICATION_CREATE, NOTIFICATION_READ, PARENT_CONTACT_READ, PARENT_CONTACT_WRITE, student_record_access,
)
from .student_record_service import (
    begin_record_write, enum_value, long_text, record_filters, require_parent, require_student, save_record,
    scoped_record, utc_datetime,
)

METHODS = {"phone": "电话", "in_person": "面谈", "sms": "短信", "email": "邮件", "other": "其他"}
CHANNELS = {"sms": "短信", "email": "邮件"}
FIELDS = ("method", "contacted_at", "content", "result")
CONTACT_CREATE_FIELDS = (*FIELDS, "parent_id", "contact_person_name", "contact_person_phone")
NOTIFICATION_FIELDS = ("channel", "content", "parent_id", "recipient_name", "recipient_address")
_CONTACT_AUDIT = ("student_id", "parent_id", "method", "contacted_at", "created_by")
_NOTIFICATION_AUDIT = ("student_id", "parent_id", "channel", "status", "created_by", "created_at")


def _history(actor, action, model, date_column, key, *, parent_id=None, page=1, per_page=20, **filters):
    scope = student_record_access(actor, action)
    conditions = record_filters(scope, date_column, utc=True, **filters)
    if parent_id is not None:
        require_parent(scope, parent_id)
        conditions.append(model.parent_id == parent_id)
    query = (select(model).join(Student).where(*conditions).options(selectinload(model.student))
             .order_by(date_column.desc(), key.desc()))
    return pagination(query, page=page, per_page=per_page)


def list_contacts(actor, **filters):
    model = ParentContactLog
    return _history(actor, PARENT_CONTACT_READ, model, model.contacted_at, model.contact_id, **filters)


def list_notifications(actor, **filters):
    model = NotificationLog
    return _history(actor, NOTIFICATION_READ, model, model.created_at, model.notification_id, **filters)


def get_contact(actor, contact_id, *, write=False):
    scope = student_record_access(actor, PARENT_CONTACT_WRITE if write else PARENT_CONTACT_READ)
    return scoped_record(scope, ParentContactLog, contact_id)


def get_notification(actor, notification_id):
    return scoped_record(student_record_access(actor, NOTIFICATION_READ), NotificationLog, notification_id)


def _parent_for_student(student_id, parent_id):
    parent = optional_relation(Parent, parent_id, "parent_id")
    if parent is not None and parent.student_id != student_id:
        raise ArchiveValidationError("parent_id", "请选择该学生所属的家长。")
    return parent


def _contact_values(data):
    return {
        "method": enum_value(data, "method", METHODS),
        "contacted_at": utc_datetime(data, "contacted_at"),
        "content": long_text(data, "content", required=True),
        "result": long_text(data, "result"),
    }


def create_contact(actor, student_id, data):
    scope = begin_record_write(actor, PARENT_CONTACT_WRITE)
    require_student(scope, student_id)
    check_fields(data, CONTACT_CREATE_FIELDS)
    parent = _parent_for_student(student_id, data.get("parent_id"))
    values = _contact_values(data)
    if parent is None:
        values["contact_person_name"] = text_value(data, "contact_person_name", 50, required=True)
        values["contact_person_phone"] = text_value(data, "contact_person_phone", 30)
    else:
        values.update(parent_id=parent.parent_id, contact_person_name=parent.name, contact_person_phone=parent.phone)
    row = ParentContactLog(student_id=student_id, created_by=actor.user_id)
    return save_record(actor, row, values, _CONTACT_AUDIT, creating=True)


def update_contact(actor, contact_id, data):
    scope = begin_record_write(actor, PARENT_CONTACT_WRITE)
    row = scoped_record(scope, ParentContactLog, contact_id, fresh=True)
    check_fields(data, FIELDS)
    return save_record(actor, row, _contact_values(data), _CONTACT_AUDIT)


def simulate_notification(actor, student_id, data):
    scope = begin_record_write(actor, NOTIFICATION_CREATE)
    require_student(scope, student_id)
    check_fields(data, NOTIFICATION_FIELDS)
    parent = _parent_for_student(student_id, data.get("parent_id"))
    channel = enum_value(data, "channel", CHANNELS)
    content = long_text(data, "content", required=True)
    address_key = "phone" if channel == "sms" else "email"
    snapshot = None
    if parent is None:
        name = text_value(data, "recipient_name", 50, required=True).strip()
        address = text_value(data, "recipient_address", 30 if channel == "sms" else 100, required=True).strip()
        if channel == "email":
            try:
                email_value({"email": address})
            except ArchiveValidationError as exc:
                raise ArchiveValidationError("recipient_address", str(exc)) from exc
        snapshot = {"name": name, address_key: address}
    elif not (getattr(parent, address_key) or "").strip():
        raise ArchiveValidationError("parent_id", "所选家长缺少此通知渠道的联系方式。")
    row = notification_service.create_simulated_notification(
        student_id, channel, content, created_by=actor.user_id,
        parent_id=parent.parent_id if parent is not None else None, recipient_snapshot=snapshot,
    )
    return save_record(actor, row, {}, _NOTIFICATION_AUDIT, creating=True)
