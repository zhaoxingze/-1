"""Student-scoped parent contacts with atomic primary-contact switching."""

from sqlalchemy import or_, select
from app.extensions import db
from app.models import Parent, Student
from .archive_common import (ArchiveValidationError,archive_write,audit,check_fields,email_value,get_record,
    pagination,require_admin,search_term,snapshot,text_value)

FIELDS=("student_id","name","relationship","phone","email","is_primary")
EDIT_FIELDS=FIELDS[1:]
RELATIONSHIPS={"father","mother","guardian","other"}


def _values(data):
    check_fields(data,EDIT_FIELDS)
    relationship=data.get("relationship")
    if relationship not in RELATIONSHIPS:raise ArchiveValidationError("relationship","家长关系无效。")
    primary=data.get("is_primary",False)
    if not isinstance(primary,bool):raise ArchiveValidationError("is_primary","主要联系人标记无效。")
    return {"name":text_value(data,"name",50,required=True),"relationship":relationship,
            "phone":text_value(data,"phone",30,required=True),"email":email_value(data)},primary


def get_parent(actor,student_id,parent_id,*,fresh=False):
    require_admin(actor);student=get_record(Student,student_id);row=get_record(Parent,parent_id,fresh=fresh)
    if row.student_id!=student.student_id:raise LookupError("Parent does not belong to student")
    return row


def _make_primary(actor,target):
    with db.session.no_autoflush:
        previous=db.session.scalars(select(Parent).where(Parent.student_id==target.student_id,
            Parent.is_primary.is_(True),Parent.parent_id!=target.parent_id).execution_options(populate_existing=True)).all()
    for row in previous:
        before=snapshot(row,FIELDS);row.is_primary=False
        db.session.flush()  # release the partial unique index before promotion
        audit(actor,row,FIELDS,before=before)
    target.is_primary=True
    db.session.flush()


@archive_write
def create_parent(actor,student_id,data):
    require_admin(actor);student=get_record(Student,student_id);values,primary=_values(data)
    row=Parent(student=student,**values,is_primary=False);db.session.add(row);db.session.flush()
    if primary:_make_primary(actor,row)
    audit(actor,row,FIELDS,action="create")
    return row


@archive_write
def update_parent(actor,student_id,parent_id,data):
    row=get_parent(actor,student_id,parent_id,fresh=True);values,primary=_values(data);before=snapshot(row,FIELDS)
    for key,value in values.items():setattr(row,key,value)
    if primary:_make_primary(actor,row)
    else:row.is_primary=False;db.session.flush()
    audit(actor,row,FIELDS,before=before)
    return row


@archive_write
def set_primary_parent(actor,student_id,parent_id):
    row=get_parent(actor,student_id,parent_id,fresh=True)
    if row.is_primary:return row
    before=snapshot(row,FIELDS);_make_primary(actor,row);audit(actor,row,FIELDS,before=before)
    return row


def list_parents(actor,*,student_id=None,q="",page=1,per_page=20):
    require_admin(actor);q=search_term(q)
    statement=select(Parent).join(Student).order_by(Parent.parent_id)
    if student_id is not None:
        student=get_record(Student,student_id);statement=statement.where(Parent.student_id==student.student_id)
    if q:statement=statement.where(or_(Parent.name.contains(q,autoescape=True),Parent.phone.contains(q,autoescape=True),
        Student.student_no.contains(q,autoescape=True),Student.name.contains(q,autoescape=True)))
    return pagination(statement,page=page,per_page=per_page)
