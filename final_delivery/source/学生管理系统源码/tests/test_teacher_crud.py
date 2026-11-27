from sqlalchemy import select
from archive_support import TEACHER_DATA,submit


def test_teacher_create_edit_and_unique_number_without_account(auth):
    from app.extensions import db
    from app.models import Teacher,User
    auth.login();response=submit(auth,'/admin/teachers/new',TEACHER_DATA)
    assert response.status_code==303
    with auth.app.app_context():
        row=db.session.scalar(select(Teacher).where(Teacher.teacher_no=='CRUD-T1'));identity=row.teacher_id
        assert db.session.scalar(select(User).where(User.teacher_id==identity)) is None
    assert submit(auth,'/admin/teachers/new',TEACHER_DATA).status_code==200
    assert submit(auth,f'/admin/teachers/{identity}/edit',{**TEACHER_DATA,'name':'修改后的虚构教师'}).status_code==303
    assert '修改后的虚构教师' in auth.client.get(response.location).text
    assert 'CRUD-T1' in auth.client.get('/admin/teachers?q=CRUD-T1').text


def test_teacher_detail_lists_related_class_and_course_without_changing_role(auth):
    from app.extensions import db
    from app.models import Teacher,SchoolClass,Course,User
    with auth.app.app_context():
        teacher=db.session.scalar(select(Teacher));identity=teacher.teacher_id
        db.session.add_all([SchoolClass(class_name='关联班',grade='G',homeroom_teacher=teacher),Course(course_code='READ-ONLY',course_name='只读关联课程',credit=1,teacher=teacher)]);db.session.commit()
    auth.login();page=auth.client.get(f'/admin/teachers/{identity}').text
    assert '关联班' in page and '只读关联课程' in page
    with auth.app.app_context():assert db.session.get(User,auth.ids['auth_teacher']).role.name=='teacher'
