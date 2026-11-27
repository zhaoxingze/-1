"""SQL aggregations for the three workbenches, with separate class and course scopes."""

from datetime import timedelta

from sqlalchemy import and_, case, func, select, true
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import AttendanceRecord, Course, Enrollment, SchoolClass, Student, Teacher
from app.models.types import utc_now
from .archive_common import ArchiveValidationError, pagination
from .attendance_service import summarize_attendance
from .enrollment_service import semester_value
from .permission_service import GRADE_READ, HOMEROOM_PROFILE, academic_access, require_current_admin, valid_scope_id

COUNT_LABELS = {
    "students": "学生总数", "enrolled": "在读学生", "archived": "已归档学生",
    "teachers": "教师总数", "classes": "班级总数", "courses": "课程总数",
    "enrollments": "本人选课", "completed": "已完成成绩课程",
}
_COMPLETE_GRADES = and_(Enrollment.usual_score.is_not(None), Enrollment.exam_score.is_not(None),
                       Enrollment.total_score.is_not(None))


def _count(model, *conditions):
    return select(func.count()).select_from(model).where(*conditions).scalar_subquery()


def _recent_attendance(student_scope, class_id=None):
    end = utc_now().date()
    start = end - timedelta(days=29)
    conditions = [student_scope, AttendanceRecord.attendance_date.between(start, end)]
    if class_id is not None:
        conditions.append(Student.class_id == class_id)
    counts, rate = summarize_attendance(*conditions)
    return {"start": start, "end": end, "attendance": counts, "rate": rate}


def _selected_class(class_id, allowed_classes, *, limited=False):
    if class_id is None:
        return None
    if not valid_scope_id(class_id) or class_id not in {row.class_id for row in allowed_classes}:
        if limited:
            raise PermissionError("Class outside workbench scope")
        raise LookupError("Class does not exist")
    return class_id


def _course_grades(course_scope, semester, course_page):
    courses = pagination(select(Course).where(course_scope).order_by(Course.course_code, Course.course_id),
                         page=course_page, per_page=10)
    course_ids = [row.course_id for row in courses.items]
    averages = {}
    if course_ids:
        query = (select(Enrollment.course_id, func.count(Enrollment.enrollment_id), func.avg(Enrollment.total_score))
                 .join(Course).where(course_scope, Enrollment.course_id.in_(course_ids),
                                    Enrollment.semester == semester, _COMPLETE_GRADES)
                 .group_by(Enrollment.course_id))
        averages = {key: (count, average) for key, count, average in db.session.execute(query)}
    return {"course_page": courses, "averages": averages}


def _class_choices(*conditions):
    return db.session.execute(select(SchoolClass.class_id, SchoolClass.grade, SchoolClass.class_name)
                              .where(*conditions).order_by(SchoolClass.grade, SchoolClass.class_name)).all()


def admin_statistics(actor, *, semester=None, class_id=None, course_page=1):
    require_current_admin(actor)
    scope = academic_access(actor, GRADE_READ)
    active = scope.active_semester
    selected = active if semester is None else semester_value(semester)
    stored = db.session.scalars(select(Enrollment.semester).distinct().order_by(Enrollment.semester.desc())).all()
    semesters = [active, *(term for term in stored if term != active)]
    if selected not in semesters:
        raise ArchiveValidationError("semester", "请选择已存在的学期。")
    classes = _class_choices()
    class_id = _selected_class(class_id, classes)
    counts = db.session.execute(select(
        _count(Student).label("students"),
        _count(Student, Student.status == "enrolled", Student.is_archived.is_(False)).label("enrolled"),
        _count(Student, Student.is_archived.is_(True)).label("archived"),
        _count(Teacher).label("teachers"), _count(SchoolClass).label("classes"), _count(Course).label("courses"),
    )).mappings().one()
    return {"counts": dict(counts), "labels": COUNT_LABELS, "semester": selected,
            "semesters": semesters, "classes": classes, "class_id": class_id,
            **_course_grades(true(), selected, course_page), **_recent_attendance(true(), class_id)}


def teacher_statistics(actor, *, semester=None, class_id=None, course_page=1):
    scope = academic_access(actor, GRADE_READ)
    if scope.role != "teacher":
        raise PermissionError("Teacher required")
    active = scope.active_semester
    if semester is not None and semester_value(semester) != active:
        raise PermissionError("Historical grades outside teacher scope")
    homeroom = SchoolClass.class_id.in_(scope.teacher.class_ids)
    students = scope.teacher.student_filter(HOMEROOM_PROFILE)
    courses = scope.courses()
    classes = _class_choices(homeroom)
    class_id = _selected_class(class_id, classes, limited=True)
    counts = db.session.execute(select(
        _count(SchoolClass, homeroom).label("classes"),
        _count(Student, students).label("students"),
        _count(Course, courses).label("courses"),
    )).mappings().one()
    return {"counts": dict(counts), "labels": {"classes": "负责班级", "students": "本班学生", "courses": "本人授课课程"},
            "semester": active, "classes": classes, "class_id": class_id,
            **_course_grades(courses, active, course_page), **_recent_attendance(students, class_id)}


def student_statistics(actor):
    scope = academic_access(actor, GRADE_READ)
    if scope.role != "student":
        raise PermissionError("Student required")
    profile = db.session.scalar(select(Student).where(Student.student_id == scope.student_id)
                                .options(selectinload(Student.school_class)))
    count, completed, average = db.session.execute(select(
        func.count(Enrollment.enrollment_id), func.count(case((_COMPLETE_GRADES, 1))),
        func.avg(case((_COMPLETE_GRADES, Enrollment.total_score))),
    ).where(scope.enrollments(), Enrollment.semester == scope.active_semester)).one()
    return {"student": profile, "average": average, "semester": scope.active_semester,
            "counts": {"enrollments": count, "completed": completed}, "labels": COUNT_LABELS,
            **_recent_attendance(Student.student_id == scope.student_id)}
