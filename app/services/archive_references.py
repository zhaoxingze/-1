"""Small administrator-only reference choices and related profile queries."""

from sqlalchemy import select
from app.extensions import db
from app.models import Course,SchoolClass,Student,Teacher
from .archive_common import get_record,pagination,require_admin


def reference_options(actor,kind):
    require_admin(actor)
    columns={"classes":(SchoolClass.class_id,SchoolClass.grade,SchoolClass.class_name),
             "teachers":(Teacher.teacher_id,Teacher.teacher_no,Teacher.name),
             "students":(Student.student_id,Student.student_no,Student.name)}
    if kind not in columns:raise ValueError("Unsupported reference kind")
    identity,code,name=columns[kind]
    return [(i,f"{c} · {n}") for i,c,n in db.session.execute(select(identity,code,name).order_by(identity))]


def teacher_relations(actor,teacher_id,*,class_page=1,course_page=1):
    require_admin(actor);teacher=get_record(Teacher,teacher_id)
    return (pagination(select(SchoolClass).where(SchoolClass.homeroom_teacher_id==teacher.teacher_id).order_by(SchoolClass.class_id),page=class_page),
            pagination(select(Course).where(Course.teacher_id==teacher.teacher_id).order_by(Course.course_id),page=course_page))
