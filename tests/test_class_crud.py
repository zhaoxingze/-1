import pytest
from sqlalchemy import select
from archive_support import CLASS_DATA,submit


@pytest.mark.parametrize('teacher_value',['0','1'])
def test_class_create_edit_student_count_and_head_teacher(auth,teacher_value):
    from app.extensions import db
    from app.models import SchoolClass,Student,Teacher
    with auth.app.app_context():
        teacher_id=db.session.scalar(select(Teacher.teacher_id))
    auth.login();data={**CLASS_DATA,'homeroom_teacher_id':'0' if teacher_value=='0' else str(teacher_id)}
    response=submit(auth,'/admin/classes/new',data);assert response.status_code==303
    with auth.app.app_context():
        row=db.session.scalar(select(SchoolClass));identity=row.class_id
        assert row.homeroom_teacher_id==(None if teacher_value=='0' else teacher_id)
        db.session.get(Student,auth.student_ids[0]).school_class=row;db.session.commit()
    assert 'AUTH-S1' in auth.client.get(response.location).text
    assert submit(auth,f'/admin/classes/{identity}/edit',{**CLASS_DATA,'homeroom_teacher_id':str(teacher_id),'class_name':'新班名'}).status_code==303


@pytest.mark.parametrize('override',[{'class_name':''},{'grade':''},{'homeroom_teacher_id':'99999'},{'homeroom_teacher_id':'bad'}])
def test_class_invalid_values_are_rejected(auth,override):
    from app.extensions import db
    from app.models import SchoolClass
    auth.login();assert submit(auth,'/admin/classes/new',{**CLASS_DATA,**override}).status_code==200
    with auth.app.app_context():assert db.session.scalar(select(SchoolClass)) is None
