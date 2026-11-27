"""Read-only administrator audit queries with an explicit display allowlist."""

from datetime import date, datetime, time
from math import isfinite

from sqlalchemy import select
from sqlalchemy.orm import load_only, selectinload

from app.extensions import db
from app.models import AuditLog, User
from app.models.security import sanitize_snapshot
from .archive_common import ArchiveValidationError, date_value, get_record, pagination, text_value
from .permission_service import require_current_admin

ACTION_LABELS = {"create": "创建", "update": "修改", "status_change": "状态变更",
                 "archive": "归档", "restore": "恢复", "delete": "删除"}
_SNAPSHOT_FIELDS = {
    "User": ("role", "student_id", "teacher_id", "is_active", "identity_changed", "operation", "changed"),
    "Student": ("class_id", "status", "is_archived", "enrollment_date"),
    "Teacher": (),
    "SchoolClass": ("homeroom_teacher_id",),
    "Parent": ("student_id", "relationship", "is_primary"),
    "Course": ("teacher_id", "credit"),
    "Enrollment": ("student_id", "course_id"),
    "AttendanceRecord": ("student_id", "attendance_date", "status", "recorded_by"),
    "RewardRecord": ("student_id", "record_type", "occurred_on", "created_by"),
    "ParentContactLog": ("student_id", "parent_id", "method", "contacted_at", "created_by"),
    "NotificationLog": ("student_id", "parent_id", "channel", "status", "created_by", "created_at"),
}
_CHOICES = {
    "role": {"admin", "teacher", "student"},
    "operation": {"self_change", "admin_reset"},
    "status": {"enrolled", "suspended", "graduated", "withdrawn", "present", "late", "absent", "leave",
               "prepared", "simulated", "cancelled"},
    "relationship": {"father", "mother", "guardian", "other"},
    "record_type": {"reward", "punishment"},
    "method": {"phone", "in_person", "sms", "email", "other"},
    "channel": {"sms", "email"},
}
_FLAGS = {"is_active", "is_archived", "is_primary", "identity_changed", "changed"}
_TIMES = {"enrollment_date", "attendance_date", "occurred_on", "contacted_at", "created_at"}
FIELD_LABELS = {
    "role": "角色", "student_id": "学生 ID", "teacher_id": "教师 ID", "is_active": "启用",
    "identity_changed": "身份绑定变化", "operation": "操作来源", "changed": "已变更",
    "class_id": "班级 ID", "status": "状态", "is_archived": "归档", "enrollment_date": "入学日期",
    "homeroom_teacher_id": "班主任 ID", "relationship": "关系", "is_primary": "主要联系人",
    "credit": "学分", "course_id": "课程 ID", "attendance_date": "考勤日期", "recorded_by": "登记者 ID",
    "record_type": "记录类型", "occurred_on": "发生日期", "created_by": "创建人 ID",
    "parent_id": "家长 ID", "method": "联系方法", "contacted_at": "联系时间（UTC）",
    "channel": "通知渠道", "created_at": "创建时间（UTC）",
}


def list_audit(actor, *, actor_user_id=None, entity_type=None, entity_id=None, action=None,
               start=None, end=None, page=1, per_page=20):
    require_current_admin(actor)
    left, right = date_value({"start": start}, "start"), date_value({"end": end}, "end")
    if left is not None and right is not None and left > right:
        raise ArchiveValidationError("end", "结束日期不能早于起始日期。")
    entity_type = text_value({"entity_type": entity_type}, "entity_type", 80)
    if action and (not isinstance(action, str) or action not in ACTION_LABELS):
        raise ArchiveValidationError("action", "操作类型无效。")
    statement = select(AuditLog).options(
        load_only(AuditLog.audit_id, AuditLog.actor_user_id, AuditLog.entity_type, AuditLog.entity_id,
                  AuditLog.action, AuditLog.created_at),
        selectinload(AuditLog.actor).load_only(User.username),
    )
    if actor_user_id is not None:
        statement = statement.where(AuditLog.actor_user_id == (None if actor_user_id == "system" else actor_user_id))
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if left is not None:
        statement = statement.where(AuditLog.created_at >= datetime.combine(left, time.min))
    if right is not None:
        statement = statement.where(AuditLog.created_at <= datetime.combine(right, time.max))
    return pagination(statement.order_by(AuditLog.created_at.desc(), AuditLog.audit_id.desc()),
                      page=page, per_page=per_page)


def audit_options(actor):
    require_current_admin(actor)
    actors = db.session.execute(select(User.user_id, User.username).join(AuditLog)
                                .distinct().order_by(User.username)).all()
    entities = db.session.scalars(select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)).all()
    return actors, entities


def _valid_value(key, value):
    if value is None:
        return True
    if key in _CHOICES:
        return isinstance(value, str) and value in _CHOICES[key]
    if key in _FLAGS:
        return type(value) is bool
    if key in _TIMES:
        if not isinstance(value, str) or len(value) > 35:
            return False
        try:
            parser = date if key.endswith("_date") or key == "occurred_on" else datetime
            return parser.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if key == "credit":
        return type(value) is int or (type(value) is float and isfinite(value))
    return type(value) is int and 0 < value <= 2**63 - 1


def _display_snapshot(entity_type, value):
    try:
        cleaned = sanitize_snapshot(value)
    except ValueError:
        return {}
    if not isinstance(cleaned, dict):
        return {}
    return {FIELD_LABELS[key]: cleaned[key] for key in _SNAPSHOT_FIELDS.get(entity_type, ())
            if key in cleaned and _valid_value(key, cleaned[key])}


def audit_detail(actor, audit_id):
    require_current_admin(actor)
    row = get_record(AuditLog, audit_id)
    return row, _display_snapshot(row.entity_type, row.before_data), _display_snapshot(row.entity_type, row.after_data)
