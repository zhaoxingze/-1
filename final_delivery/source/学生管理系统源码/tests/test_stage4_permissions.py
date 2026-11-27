import pytest
from archive_support import STUDENT_DATA,submit,actor

MANAGEMENT_PATHS=['/admin/students','/admin/students/new','/admin/students/1','/admin/students/1/edit','/admin/students/1/status','/admin/students/1/archive','/admin/students/1/restore','/admin/teachers','/admin/teachers/new','/admin/teachers/1','/admin/teachers/1/edit','/admin/classes','/admin/classes/new','/admin/classes/1','/admin/classes/1/edit','/admin/parents','/admin/students/1/parents','/admin/students/1/parents/new','/admin/students/1/parents/1','/admin/students/1/parents/1/edit','/admin/students/1/parents/1/primary']


@pytest.mark.parametrize('path',MANAGEMENT_PATHS)
def test_all_management_gets_require_login(client,path):
    response=client.get(path);assert response.status_code==302 and response.location.startswith('/login?next=')


@pytest.mark.parametrize('username',['auth_teacher','auth_student'])
def test_every_management_get_and_write_denies_other_roles(auth,username):
    auth.login(username);token=auth.token('/profile')
    for path in MANAGEMENT_PATHS:
        assert auth.client.get(path).status_code==403,path
        if any(part in path for part in ('/new','/edit','/status','/archive','/restore','/primary')):
            assert auth.client.post(path,data={'csrf_token':token,'role_id':17,**STUDENT_DATA}).status_code==403,path
    assert auth.client.get('/profile').status_code==200


def test_csrf_confirmation_and_get_requests_cannot_mutate(auth):
    from app.extensions import db
    from app.models import Student
    auth.login();identity=auth.student_ids[0]
    for path in ('/admin/students/new',f'/admin/students/{identity}/archive',f'/admin/students/{identity}/status'):
        assert auth.client.post(path,data=STUDENT_DATA).status_code==400
    assert submit(auth,f'/admin/students/{identity}/archive',{}).status_code==200
    with auth.app.app_context():assert not db.session.get(Student,identity).is_archived


@pytest.mark.parametrize('query',['page=0','page=no','per_page=101','class_id=bad','archived=unknown'])
def test_malformed_list_parameters_are_rejected(auth,query):
    auth.login();assert auth.client.get('/admin/students?'+query).status_code==400


def test_services_recheck_actor_permissions(auth):
    from app.extensions import db
    from app.models import User
    from app.services.student_service import create_student,list_students
    with auth.app.app_context():
        teacher=db.session.get(User,auth.ids['auth_teacher'])
        with pytest.raises(PermissionError):create_student(teacher,STUDENT_DATA)
        with pytest.raises(PermissionError):list_students(teacher)


@pytest.mark.parametrize('value',['false',''])
def test_explicit_negative_confirmation_cannot_archive(auth,value):
    from app.extensions import db
    from app.models import Student
    auth.login();path=f'/admin/students/{auth.student_ids[0]}/archive'
    assert submit(auth,path,{'confirm':value}).status_code==200
    with auth.app.app_context():assert not db.session.get(Student,auth.student_ids[0]).is_archived


def test_large_valid_entity_ids_can_be_used_as_filters(auth):
    from app.extensions import db
    from app.models import SchoolClass,Student
    with auth.app.app_context():
        c=SchoolClass(class_id=3000000000,class_name='高位班级',grade='G')
        s=Student(student_id=3000000001,student_no='HIGH-S',name='高位学生',gender='未指定',enrollment_date=__import__('datetime').date(2026,9,1),school_class=c)
        db.session.add_all([c,s]);db.session.commit()
    auth.login()
    assert auth.client.get('/admin/students?class_id=3000000000').status_code==200
    assert auth.client.get('/admin/parents?student_id=3000000001').status_code==200
