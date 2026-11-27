"""Term-specific enrollment creation, listings and selectors."""

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Course, Enrollment, Student
from .archive_common import ArchiveValidationError, audit, begin_archive_write, get_record, pagination, search_term, text_value
from .course_service import scoped_course
from .permission_service import (
    ENROLLMENT_CREATE, ENROLLMENT_READ, GRADE_READ, academic_access, valid_scope_id,
)

ENROLLMENT_FIELDS = ("student_id", "course_id", "semester", "usual_score", "exam_score", "total_score")


def semester_value(value):
    return text_value({"semester": value}, "semester", 30, required=True)


def semester_options(actor, action=ENROLLMENT_READ, *, course_id=None):
    scope = academic_access(actor, action)
    statement = select(Enrollment.semester).where(scope.enrollments())
    if course_id is not None:
        scoped_course(scope, course_id)
        statement = statement.where(Enrollment.course_id == course_id)
    terms = db.session.scalars(statement.distinct().order_by(Enrollment.semester.desc())).all()
    return [scope.active_semester, *(term for term in terms if term != scope.active_semester)]


def course_options(actor, action=ENROLLMENT_READ):
    scope = academic_access(actor, action)
    return db.session.execute(select(Course.course_id, Course.course_code, Course.course_name)
                              .where(scope.courses()).order_by(Course.course_code)).all()


def enrollment_candidates(actor):
    scope = academic_access(actor, ENROLLMENT_CREATE)
    return db.session.execute(select(Student.student_id, Student.student_no, Student.name)
                              .where(scope.enrollment_candidates()).order_by(Student.student_no)).all()


def list_enrollments(actor, *, action=ENROLLMENT_READ, semester=None, course_id=None,
                     student_id=None, q="", page=1, per_page=20):
    if action not in (ENROLLMENT_READ, GRADE_READ):
        raise PermissionError("Academic read action required")
    scope = academic_access(actor, action)
    statement = select(Enrollment).join(Student).join(Course).where(scope.enrollments())
    statement = statement.options(selectinload(Enrollment.student), selectinload(Enrollment.course))
    if semester is not None:
        semester = semester_value(semester)
        if scope.teacher and action == GRADE_READ and semester != scope.active_semester:
            raise PermissionError("Historical grades outside teacher scope")
        statement = statement.where(Enrollment.semester == semester)
    if course_id is not None:
        scoped_course(scope, course_id)
        statement = statement.where(Enrollment.course_id == course_id)
    if student_id is not None:
        if not valid_scope_id(student_id) or (scope.role == "student" and scope.student_id != student_id):
            raise PermissionError("Student outside academic scope")
        statement = statement.where(Enrollment.student_id == student_id)
    q = search_term(q)
    if q:
        statement = statement.where(or_(
            Student.student_no.contains(q, autoescape=True), Student.name.contains(q, autoescape=True),
            Course.course_code.contains(q, autoescape=True), Course.course_name.contains(q, autoescape=True),
        ))
    return pagination(statement.order_by(Enrollment.semester.desc(), Enrollment.enrollment_id),
                      page=page, per_page=per_page)


def create_enrollment(actor, student_id, course_id, semester):
    academic_access(actor, ENROLLMENT_CREATE)
    begin_archive_write()
    scope = academic_access(actor, ENROLLMENT_CREATE)
    semester = semester_value(semester)
    if scope.teacher and semester != scope.active_semester:
        raise PermissionError("Enrollment term outside teacher scope")
    course = scoped_course(scope, course_id, fresh=True)
    if scope.teacher:
        if not valid_scope_id(student_id) or db.session.scalar(select(Student.student_id).where(
                Student.student_id == student_id, scope.enrollment_candidates())) is None:
            raise PermissionError("Student outside homeroom scope")
    else:
        student_id = get_record(Student, student_id, fresh=True).student_id
    if db.session.scalar(select(Enrollment.enrollment_id).where(
        Enrollment.student_id == student_id, Enrollment.course_id == course.course_id, Enrollment.semester == semester
    )) is not None:
        raise ArchiveValidationError("student_id", "该学生在此学期已选这门课程。")
    row = Enrollment(student_id=student_id, course_id=course.course_id, semester=semester,
                     usual_score=None, exam_score=None, total_score=None)
    db.session.add(row)
    db.session.flush()
    audit(actor, row, ENROLLMENT_FIELDS, action="create")
    return row
