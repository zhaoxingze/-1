"""Scoped teacher queries and contact updates against current relationships."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Bundle

from app.extensions import db
from app.models import Course, Parent, SchoolClass, Student
from .archive_common import (
    ArchiveValidationError, audit, begin_archive_write, check_fields, pagination,
    search_term, snapshot, text_value,
)
from .permission_service import (
    COURSE_IDENTITY, EDIT_CONTACT, HOMEROOM_PROFILE, PARENT_CONTACT,
    get_teacher_scope, require_teacher_student_access, valid_scope_id,
)

CONTACT_FIELDS = ("phone", "address")


def list_owned_classes(actor, *, page=1, per_page=20):
    scope = get_teacher_scope(actor)
    statement = select(SchoolClass).where(SchoolClass.class_id.in_(scope.class_ids))
    return pagination(statement.order_by(SchoolClass.class_id), page=page, per_page=per_page)


def list_owned_courses(actor, *, page=1, per_page=20):
    scope = get_teacher_scope(actor)
    statement = select(Course).where(Course.course_id.in_(scope.course_ids))
    return pagination(statement.order_by(Course.course_id), page=page, per_page=per_page)


def _require_result(statement):
    result = db.session.execute(statement).one_or_none()
    if result is None:
        raise PermissionError("Record outside teacher scope")
    return result


def _filter_roster(statement, q):
    q = search_term(q)
    if q:
        statement = statement.where(or_(
            Student.student_no.contains(q, autoescape=True),
            Student.name.contains(q, autoescape=True),
        ))
    return statement.order_by(Student.student_id)


def list_class_students(actor, class_id, *, q="", page=1, per_page=20):
    scope = get_teacher_scope(actor)
    if not valid_scope_id(class_id):
        raise PermissionError("Class outside teacher scope")
    school_class = _require_result(select(SchoolClass.class_name, SchoolClass.grade).where(
        SchoolClass.class_id == class_id, SchoolClass.class_id.in_(scope.class_ids)
    ))
    fields = Bundle("identity", Student.student_id, Student.student_no, Student.name)
    statement = select(fields).where(
        Student.class_id == class_id, scope.student_filter(HOMEROOM_PROFILE)
    )
    return school_class, pagination(_filter_roster(statement, q), page=page, per_page=per_page)


def list_course_students(actor, course_id, *, q="", page=1, per_page=20):
    scope = get_teacher_scope(actor)
    if not valid_scope_id(course_id):
        raise PermissionError("Course outside teacher scope")
    course = _require_result(select(Course.course_code, Course.course_name).where(
        Course.course_id == course_id, Course.course_id.in_(scope.course_ids)
    ))
    fields = Bundle("identity", Student.student_no, Student.name)
    statement = select(fields).where(scope.student_filter(COURSE_IDENTITY, course_id=course_id))
    return course, pagination(_filter_roster(statement, q), page=page, per_page=per_page)


def get_homeroom_student(actor, student_id, *, action=HOMEROOM_PROFILE):
    if action not in (HOMEROOM_PROFILE, EDIT_CONTACT, PARENT_CONTACT):
        raise PermissionError("Unsupported homeroom action")
    scope = require_teacher_student_access(actor, student_id, action=action)
    return _require_result(select(
        Student.student_id, Student.student_no, Student.name, SchoolClass.class_name,
        Student.phone, Student.address,
    ).join(SchoolClass).where(
        Student.student_id == student_id, scope.student_filter(action)
    ))


def list_parent_contacts(actor, student_id, *, page=1, per_page=20):
    scope = require_teacher_student_access(actor, student_id, action=PARENT_CONTACT)
    fields = Bundle("contact", Parent.name, Parent.relationship, Parent.phone, Parent.email, Parent.is_primary)
    statement = select(fields).join(Student).where(
        Student.student_id == student_id, scope.student_filter(PARENT_CONTACT)
    ).order_by(Parent.is_primary.desc(), Parent.parent_id)
    return pagination(statement, page=page, per_page=per_page)


def update_student_contact(actor, student_id, data):
    check_fields(data, CONTACT_FIELDS)
    if not data:
        raise ArchiveValidationError(None, "请提交需要更新的联系方式。")
    values = {field: text_value(data, field, maximum)
              for field, maximum in (("phone", 30), ("address", 255)) if field in data}
    get_teacher_scope(actor)
    begin_archive_write()
    scope = require_teacher_student_access(actor, student_id, action=EDIT_CONTACT)
    with db.session.no_autoflush:
        student = db.session.scalar(select(Student).where(
            Student.student_id == student_id, scope.student_filter(EDIT_CONTACT)
        ).execution_options(populate_existing=True))
    if student is None:
        raise PermissionError("Student outside teacher scope")
    before = snapshot(student, CONTACT_FIELDS)
    for field, value in values.items():
        setattr(student, field, value)
    db.session.flush()
    audit(actor, student, CONTACT_FIELDS, before=before)
    return student.student_id
