"""Attendance writes, scoped history and attendance-rate calculation."""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import AttendanceRecord, Student
from .archive_common import ArchiveValidationError, check_fields, date_value, pagination, text_value
from .permission_service import ATTENDANCE_READ, ATTENDANCE_WRITE, student_record_access
from .student_record_service import (
    begin_record_write, enum_value, record_filters, require_student, save_record, scoped_record,
)

STATUSES = {"present": "出勤", "late": "迟到", "absent": "缺勤", "leave": "请假"}
FIELDS = ("attendance_date", "period", "status", "note")
_AUDIT_FIELDS = ("student_id", "attendance_date", "period", "status", "recorded_by")


def list_attendance(actor, *, page=1, per_page=20, **filters):
    scope = student_record_access(actor, ATTENDANCE_READ)
    conditions = record_filters(scope, AttendanceRecord.attendance_date, **filters)
    query = (select(AttendanceRecord).join(Student).where(*conditions)
             .options(selectinload(AttendanceRecord.student))
             .order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.attendance_id.desc()))
    return pagination(query, page=page, per_page=per_page)


def attendance_statistics(actor, **filters):
    scope = student_record_access(actor, ATTENDANCE_READ)
    conditions = record_filters(scope, AttendanceRecord.attendance_date, **filters)
    return summarize_attendance(*conditions)


def summarize_attendance(*conditions):
    """Aggregate a caller's already-authorized attendance conditions."""
    rows = db.session.execute(select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_id))
                              .join(Student).where(*conditions).group_by(AttendanceRecord.status))
    counts = dict.fromkeys(STATUSES, 0)
    counts.update(rows.all())
    present = counts["present"] + counts["late"]
    denominator = present + counts["absent"]
    rate = (Decimal(present * 100) / denominator).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if denominator else None
    return counts, rate


def get_attendance(actor, attendance_id, *, write=False):
    scope = student_record_access(actor, ATTENDANCE_WRITE if write else ATTENDANCE_READ)
    return scoped_record(scope, AttendanceRecord, attendance_id)


def _values(data):
    check_fields(data, FIELDS)
    return {
        "attendance_date": date_value(data, "attendance_date", required=True),
        "period": text_value(data, "period", 30, required=True).strip(),
        "status": enum_value(data, "status", STATUSES),
        "note": text_value(data, "note", 255),
    }


def _save(actor, row, data, *, creating):
    values = _values(data)
    duplicate = select(AttendanceRecord.attendance_id).where(
        AttendanceRecord.student_id == row.student_id,
        AttendanceRecord.attendance_date == values["attendance_date"],
        AttendanceRecord.period == values["period"],
    )
    if not creating:
        duplicate = duplicate.where(AttendanceRecord.attendance_id != row.attendance_id)
    if db.session.scalar(duplicate) is not None:
        raise ArchiveValidationError("period", "该学生在此日期与节次已登记考勤。")
    return save_record(actor, row, {**values, "recorded_by": actor.user_id}, _AUDIT_FIELDS, creating=creating)


def create_attendance(actor, student_id, data):
    scope = begin_record_write(actor, ATTENDANCE_WRITE)
    require_student(scope, student_id)
    return _save(actor, AttendanceRecord(student_id=student_id), data, creating=True)


def update_attendance(actor, attendance_id, data):
    scope = begin_record_write(actor, ATTENDANCE_WRITE)
    row = scoped_record(scope, AttendanceRecord, attendance_id, fresh=True)
    return _save(actor, row, data, creating=False)
