"""Reward and disciplinary history management under current student scope."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import RewardRecord, Student
from .archive_common import check_fields, date_value, pagination, text_value
from .permission_service import REWARD_READ, REWARD_WRITE, student_record_access
from .student_record_service import (
    begin_record_write, enum_value, long_text, record_filters, require_student, save_record, scoped_record,
)

RECORD_TYPES = {"reward": "奖励", "punishment": "处分"}
FIELDS = ("record_type", "category", "description", "occurred_on")
_AUDIT_FIELDS = ("student_id", "record_type", "category", "occurred_on", "created_by")


def list_rewards(actor, *, record_type=None, category=None, page=1, per_page=20, **filters):
    scope = student_record_access(actor, REWARD_READ)
    conditions = record_filters(scope, RewardRecord.occurred_on, **filters)
    if record_type:
        conditions.append(RewardRecord.record_type == enum_value({"record_type": record_type}, "record_type", RECORD_TYPES))
    category = text_value({"category": category}, "category", 50)
    if category is not None:
        conditions.append(RewardRecord.category.contains(category.strip(), autoescape=True))
    query = (select(RewardRecord).join(Student).where(*conditions).options(selectinload(RewardRecord.student))
             .order_by(RewardRecord.occurred_on.desc(), RewardRecord.record_id.desc()))
    return pagination(query, page=page, per_page=per_page)


def get_reward(actor, record_id, *, write=False):
    scope = student_record_access(actor, REWARD_WRITE if write else REWARD_READ)
    return scoped_record(scope, RewardRecord, record_id)


def _values(data):
    check_fields(data, FIELDS)
    return {
        "record_type": enum_value(data, "record_type", RECORD_TYPES),
        "category": text_value(data, "category", 50, required=True).strip(),
        "description": long_text(data, "description", required=True),
        "occurred_on": date_value(data, "occurred_on", required=True),
    }


def create_reward(actor, student_id, data):
    scope = begin_record_write(actor, REWARD_WRITE)
    require_student(scope, student_id)
    row = RewardRecord(student_id=student_id, created_by=actor.user_id)
    return save_record(actor, row, _values(data), _AUDIT_FIELDS, creating=True)


def update_reward(actor, record_id, data):
    scope = begin_record_write(actor, REWARD_WRITE)
    row = scoped_record(scope, RewardRecord, record_id, fresh=True)
    return save_record(actor, row, _values(data), _AUDIT_FIELDS)
