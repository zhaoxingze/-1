"""Current classes, optional homeroom teacher and student counts."""

from sqlalchemy import func, or_, select
from app.extensions import db
from app.models import SchoolClass, Student, Teacher
from .archive_common import (archive_write,audit,check_fields,get_record,optional_relation,pagination,
    require_admin,search_term,snapshot,text_value)

FIELDS=("class_name","grade","homeroom_teacher_id")


def _values(data):
    check_fields(data,FIELDS)
    return {"class_name":text_value(data,"class_name",50,required=True),
            "grade":text_value(data,"grade",30,required=True),
            "homeroom_teacher":optional_relation(Teacher,data.get("homeroom_teacher_id"),"homeroom_teacher_id")}


@archive_write
def create_class(actor,data):
    require_admin(actor);row=SchoolClass(**_values(data));db.session.add(row);db.session.flush()
    audit(actor,row,FIELDS,action="create")
    return row


def get_class(actor,class_id,*,fresh=False):
    require_admin(actor)
    return get_record(SchoolClass,class_id,fresh=fresh)


@archive_write
def update_class(actor,class_id,data):
    row=get_class(actor,class_id,fresh=True);values=_values(data);before=snapshot(row,FIELDS)
    for key,value in values.items():setattr(row,key,value)
    db.session.flush();audit(actor,row,FIELDS,before=before)
    return row


def list_classes(actor,*,q="",page=1,per_page=20):
    require_admin(actor);q=search_term(q)
    statement=select(SchoolClass).order_by(SchoolClass.class_id)
    if q:statement=statement.where(or_(SchoolClass.class_name.contains(q,autoescape=True),SchoolClass.grade.contains(q,autoescape=True)))
    return pagination(statement,page=page,per_page=per_page)


def student_counts(actor,class_ids):
    require_admin(actor)
    return dict(db.session.execute(select(Student.class_id,func.count()).where(Student.class_id.in_(class_ids)).group_by(Student.class_id)).all())
