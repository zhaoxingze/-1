"""Course reads and administrator writes against the existing Course model."""

from decimal import Decimal
from math import isfinite

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Course, Enrollment, Teacher
from .archive_common import (
    ArchiveValidationError, archive_write, audit, check_fields, check_unique,
    get_record, optional_relation, pagination, search_term, snapshot, text_value,
)
from .permission_service import COURSE_MANAGE, COURSE_READ, ENROLLMENT_READ, academic_access, valid_scope_id

COURSE_FIELDS = ("course_code", "course_name", "credit", "teacher_id", "description")


def scoped_course(scope, course_id, *, fresh=False):
    if scope.role == "admin":
        return get_record(Course, course_id, fresh=fresh)
    if not valid_scope_id(course_id):
        raise PermissionError("Course outside scope")
    statement = select(Course).where(Course.course_id == course_id, scope.courses())
    row = db.session.scalar(statement.execution_options(populate_existing=fresh))
    if row is None:
        raise PermissionError("Course outside scope")
    return row


def get_course(actor, course_id):
    return scoped_course(academic_access(actor, COURSE_READ), course_id)


def list_courses(actor, *, q="", page=1, per_page=20):
    scope = academic_access(actor, COURSE_READ)
    q = search_term(q)
    statement = select(Course).where(scope.courses()).options(selectinload(Course.teacher))
    if q:
        statement = statement.where(or_(Course.course_code.contains(q, autoescape=True),
                                        Course.course_name.contains(q, autoescape=True)))
    return pagination(statement.order_by(Course.course_code, Course.course_id), page=page, per_page=per_page)


def count_course_enrollments(actor, course_id, semester):
    from .enrollment_service import semester_value

    scope = academic_access(actor, ENROLLMENT_READ)
    semester = semester_value(semester)
    scoped_course(scope, course_id)
    return db.session.scalar(select(func.count(Enrollment.enrollment_id)).where(
        scope.enrollments(), Enrollment.course_id == course_id, Enrollment.semester == semester
    ))


def _course_values(data):
    check_fields(data, COURSE_FIELDS)
    credit = data.get("credit")
    if type(credit) not in (Decimal, int, float):
        raise ArchiveValidationError("credit", "请输入有效学分。")
    try:
        credit = float(credit)
    except (OverflowError, ValueError):
        raise ArchiveValidationError("credit", "请输入可存储的有限学分。") from None
    if not isfinite(credit):
        raise ArchiveValidationError("credit", "请输入可存储的有限学分。")
    description = data.get("description")
    if description is not None and (not isinstance(description, str) or "\x00" in description):
        raise ArchiveValidationError("description", "课程说明格式无效。")
    teacher = optional_relation(Teacher, data.get("teacher_id"), "teacher_id")
    return {
        "course_code": text_value(data, "course_code", 30, required=True),
        "course_name": text_value(data, "course_name", 100, required=True),
        "credit": credit,
        "teacher_id": teacher.teacher_id if teacher is not None else None,
        "description": description if description else None,
    }


@archive_write
def create_course(actor, data):
    academic_access(actor, COURSE_MANAGE)
    values = _course_values(data)
    check_unique(Course, "course_code", values["course_code"])
    row = Course(**values)
    db.session.add(row)
    db.session.flush()
    audit(actor, row, COURSE_FIELDS, action="create")
    return row


@archive_write
def update_course(actor, course_id, data):
    scope = academic_access(actor, COURSE_MANAGE)
    row = scoped_course(scope, course_id, fresh=True)
    values = _course_values(data)
    check_unique(Course, "course_code", values["course_code"], excluding=row.course_id)
    before = snapshot(row, COURSE_FIELDS)
    for field, value in values.items():
        setattr(row, field, value)
    db.session.flush()
    audit(actor, row, COURSE_FIELDS, before=before)
    return row
