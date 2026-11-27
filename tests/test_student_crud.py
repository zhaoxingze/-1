from datetime import date
import pytest
from sqlalchemy import select
from archive_support import STUDENT_DATA,submit,actor


def test_admin_can_create_read_edit_student(auth):
    from app.extensions import db
    from app.models import Student,User
    auth.login()
    response=submit(auth,'/admin/students/new',STUDENT_DATA)
    assert response.status_code==303
    with auth.app.app_context():
        row=db.session.scalar(select(Student).where(Student.student_no=='CRUD-S1'))
        identity=row.student_id
        assert row.status=='enrolled' and not row.is_archived and row.class_id is None
        assert db.session.scalar(select(User).where(User.student_id==identity)) is None
    assert '虚构档案学生' in auth.client.get(response.location).text
    data={**STUDENT_DATA,'name':'修改后的虚构学生'}
    assert submit(auth,f'/admin/students/{identity}/edit',data).status_code==303
    assert '修改后的虚构学生' in auth.client.get(f'/admin/students/{identity}').text


@pytest.mark.parametrize('override',[{'student_no':'AUTH-S1'},{'name':''},{'gender':''},{'student_no':' '},{'class_id':'999999'},{'birth_date':'2025-02-29'},{'enrollment_date':'bad-date'},{'student_no':'x'*31},{'class_id':'-2'}])
def test_student_invalid_fields_do_not_write(auth,override):
    from app.extensions import db
    from app.models import Student,AuditLog
    auth.login();response=submit(auth,'/admin/students/new',{**STUDENT_DATA,**override})
    assert response.status_code==200
    assert '保存成功' not in response.text
    with auth.app.app_context():
        assert len(db.session.scalars(select(Student)).all())==2
        assert db.session.scalar(select(AuditLog)) is None


@pytest.mark.parametrize('old,new',[('enrolled','suspended'),('enrolled','graduated'),('enrolled','withdrawn'),('suspended','enrolled'),('suspended','withdrawn')])
def test_only_documented_state_edges_succeed(auth,old,new):
    from app.extensions import db
    from app.models import Student
    from app.services.student_service import change_student_status
    with auth.app.app_context():
        row=db.session.get(Student,auth.student_ids[0]);row.status=old;db.session.commit()
        change_student_status(actor(auth),row.student_id,new);db.session.commit()
        assert row.status==new


@pytest.mark.parametrize('old,new',[('suspended','graduated'),('graduated','enrolled'),('withdrawn','enrolled'),('enrolled','enrolled'),('enrolled','disabled')])
def test_illegal_state_edges_are_rejected(auth,old,new):
    from app.extensions import db
    from app.models import Student,AuditLog
    from app.services.student_service import change_student_status
    with auth.app.app_context():
        row=db.session.get(Student,auth.student_ids[0]);row.status=old;db.session.commit()
        with pytest.raises(ValueError):change_student_status(actor(auth),row.student_id,new)
        assert row.status==old and db.session.scalar(select(AuditLog)) is None


def test_student_archive_restore_preserves_account_and_history(auth):
    from app.extensions import db
    from app.models import Student,User,AttendanceRecord
    with auth.app.app_context():
        db.session.add(AttendanceRecord(student_id=auth.student_ids[0],attendance_date=date(2026,11,18),period='A1',status='present',recorded_by=auth.ids['auth_admin']));db.session.commit()
    auth.login();path=f'/admin/students/{auth.student_ids[0]}'
    assert auth.client.get(path+'/archive').status_code==200
    with auth.app.app_context():assert not db.session.get(Student,auth.student_ids[0]).is_archived
    assert submit(auth,path+'/archive',{'confirm':'y'}).status_code==303
    with auth.app.app_context():
        row=db.session.get(Student,auth.student_ids[0]);assert row.is_archived and row.status=='enrolled'
        assert db.session.get(User,auth.ids['auth_student']).is_active
        assert db.session.scalar(select(AttendanceRecord)) is not None
    assert 'AUTH-S1' not in auth.client.get('/admin/students').text
    assert 'AUTH-S1' in auth.client.get('/admin/students?archived=archived').text
    assert submit(auth,path+'/restore',{'confirm':'y'}).status_code==303


def test_search_class_filter_pagination_and_age(auth):
    from app.extensions import db
    from app.models import SchoolClass,Student
    from app.services.student_service import calculate_age
    with auth.app.app_context():
        school_class=SchoolClass(class_name='筛选班',grade='G1');db.session.add(school_class);db.session.flush()
        db.session.get(Student,auth.student_ids[0]).school_class=school_class;db.session.commit();cid=school_class.class_id
        assert calculate_age(date(2008,11,19),on_date=date(2026,11,18))==17
        assert calculate_age(date(2008,11,18),on_date=date(2026,11,18))==18
        assert calculate_age(None) is None
    auth.login()
    assert 'AUTH-S1' in auth.client.get(f'/admin/students?class_id={cid}&q=AUTH-S1').text
    assert 'AUTH-S2' not in auth.client.get(f'/admin/students?class_id={cid}').text
    assert 'AUTH-S1' not in auth.client.get('/admin/students?q=%25').text
    assert 'AUTH-S2' in auth.client.get('/admin/students?per_page=1&page=2').text
    assert auth.client.get('/admin/students?page=999').status_code==404


def test_standard_edit_cannot_inject_status_archive_or_account(auth):
    from app.extensions import db
    from app.models import Student,User
    auth.login();identity=auth.student_ids[0]
    data={**STUDENT_DATA,'student_no':'AUTH-S1','status':'graduated','is_archived':'y','is_active':''}
    assert submit(auth,f'/admin/students/{identity}/edit',data).status_code==303
    with auth.app.app_context():
        student=db.session.get(Student,identity)
        assert student.status=='enrolled' and not student.is_archived
        assert db.session.get(User,auth.ids['auth_student']).is_active


def test_web_status_flow_and_duplicate_edit_rollback(auth):
    from app.extensions import db
    from app.models import Student
    auth.login();identity=auth.student_ids[0];path=f'/admin/students/{identity}'
    assert submit(auth,path+'/status',{'status':'suspended'}).status_code==303
    assert submit(auth,path+'/status',{'status':'graduated'}).status_code==200
    assert submit(auth,path+'/edit',{**STUDENT_DATA,'student_no':'AUTH-S2'}).status_code==200
    with auth.app.app_context():
        row=db.session.get(Student,identity);assert row.status=='suspended' and row.student_no=='AUTH-S1'


def test_empty_class_filter_service_means_all_students(auth):
    from app.services.student_service import list_students
    with auth.app.app_context():assert list_students(actor(auth),class_id='').total==2
