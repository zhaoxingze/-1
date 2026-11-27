"""Administrator student archives; status and archival use distinct actions."""

from datetime import date
from sqlalchemy import or_, select

from app.extensions import db
from app.models import SchoolClass, Student
from .archive_common import (ArchiveValidationError, archive_write, audit, check_fields, check_unique,
    date_value, get_record, optional_relation, pagination, require_admin, search_term,
    snapshot, text_value)

FIELDS = ("student_no", "name", "gender", "birth_date", "phone", "address", "class_id", "enrollment_date", "status", "is_archived")
EDIT_FIELDS = FIELDS[:-2]
STATE_TRANSITIONS = {"enrolled": {"suspended", "graduated", "withdrawn"},
                     "suspended": {"enrolled", "withdrawn"}, "graduated": set(), "withdrawn": set()}


def calculate_age(birth_date, *, on_date=None):
    today = on_date or date.today()
    if birth_date is None or birth_date > today:
        return None
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _values(data):
    check_fields(data, EDIT_FIELDS)
    values = {field: text_value(data, field, maximum, required=required)
              for field, maximum, required in (("student_no",30,True),("name",50,True),
                  ("gender",10,True),("phone",30,False),("address",255,False))}
    values["birth_date"] = date_value(data, "birth_date")
    values["enrollment_date"] = date_value(data, "enrollment_date", required=True)
    values["school_class"] = optional_relation(SchoolClass, data.get("class_id"), "class_id")
    return values


@archive_write
def create_student(actor, data):
    require_admin(actor)
    values = _values(data)
    check_unique(Student, "student_no", values["student_no"])
    row = Student(**values, status="enrolled", is_archived=False)
    db.session.add(row); db.session.flush()
    audit(actor, row, FIELDS, action="create")
    return row


def get_student(actor, student_id, *, fresh=False):
    require_admin(actor)
    return get_record(Student, student_id, fresh=fresh)


@archive_write
def update_student(actor, student_id, data):
    row = get_student(actor, student_id, fresh=True)
    values = _values(data)
    check_unique(Student, "student_no", values["student_no"], excluding=row.student_id)
    before = snapshot(row, FIELDS)
    for key, value in values.items():
        setattr(row, key, value)
    db.session.flush(); audit(actor, row, FIELDS, before=before)
    return row


@archive_write
def change_student_status(actor, student_id, target):
    row = get_student(actor, student_id, fresh=True)
    if target not in STATE_TRANSITIONS.get(row.status, set()):
        raise ArchiveValidationError("status", "不允许此学籍状态迁移。")
    before = snapshot(row, FIELDS); row.status = target
    db.session.flush(); audit(actor, row, FIELDS, before=before, action="status_change")
    return row


@archive_write
def set_student_archived(actor, student_id, archived):
    row = get_student(actor, student_id, fresh=True)
    if not isinstance(archived, bool):
        raise ArchiveValidationError(None, "归档标记无效。")
    if row.is_archived == archived:
        raise ArchiveValidationError(None, "档案已处于该归档状态。")
    before = snapshot(row, FIELDS); row.is_archived = archived
    db.session.flush(); audit(actor, row, FIELDS, before=before, action="archive" if archived else "restore")
    return row


def list_students(actor, *, q="", class_id=None, archived="active", page=1, per_page=20):
    require_admin(actor); q = search_term(q)
    statement = select(Student).outerjoin(SchoolClass).order_by(Student.student_id)
    if q:
        statement = statement.where(or_(Student.student_no.contains(q, autoescape=True),
            Student.name.contains(q, autoescape=True), SchoolClass.class_name.contains(q, autoescape=True)))
    if class_id not in (None, ""):
        school_class = optional_relation(SchoolClass, class_id, "class_id")
        statement = statement.where(Student.class_id == school_class.class_id)
    if archived not in {"active", "archived", "all"}:
        raise ArchiveValidationError(None, "归档筛选无效。")
    if archived != "all":
        statement = statement.where(Student.is_archived.is_(archived == "archived"))
    return pagination(statement, page=page, per_page=per_page)
