"""Teacher profiles do not create or change accounts."""

from sqlalchemy import or_, select
from app.extensions import db
from app.models import Teacher
from .archive_common import (archive_write, audit, check_fields, check_unique, email_value, get_record,
    pagination, require_admin, search_term, snapshot, text_value)

FIELDS = ("teacher_no", "name", "phone", "email")


def _values(data):
    check_fields(data, FIELDS)
    return {"teacher_no":text_value(data,"teacher_no",30,required=True),
            "name":text_value(data,"name",50,required=True),"phone":text_value(data,"phone",30),"email":email_value(data)}


@archive_write
def create_teacher(actor, data):
    require_admin(actor); values = _values(data)
    check_unique(Teacher,"teacher_no",values["teacher_no"])
    row = Teacher(**values); db.session.add(row); db.session.flush()
    audit(actor,row,FIELDS,action="create")
    return row


def get_teacher(actor, teacher_id, *, fresh=False):
    require_admin(actor)
    return get_record(Teacher,teacher_id,fresh=fresh)


@archive_write
def update_teacher(actor, teacher_id, data):
    row = get_teacher(actor,teacher_id,fresh=True); values = _values(data)
    check_unique(Teacher,"teacher_no",values["teacher_no"],excluding=row.teacher_id)
    before = snapshot(row,FIELDS)
    for key,value in values.items():setattr(row,key,value)
    db.session.flush();audit(actor,row,FIELDS,before=before)
    return row


def list_teachers(actor, *, q="", page=1, per_page=20):
    require_admin(actor);q=search_term(q)
    statement=select(Teacher).order_by(Teacher.teacher_id)
    if q:statement=statement.where(or_(Teacher.teacher_no.contains(q,autoescape=True),Teacher.name.contains(q,autoescape=True)))
    return pagination(statement,page=page,per_page=per_page)
