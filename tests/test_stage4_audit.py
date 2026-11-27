import pytest
from sqlalchemy import select,text
from archive_support import STUDENT_DATA,TEACHER_DATA,CLASS_DATA,PARENT_DATA,actor,submit


def test_each_domain_write_records_actor_fields_and_actions_without_commit(auth):
    from app.extensions import db
    from app.models import AuditLog,Student
    from app.services.student_service import create_student,update_student,change_student_status,set_student_archived
    from app.services.teacher_service import create_teacher,update_teacher
    from app.services.class_service import create_class,update_class
    from app.services.parent_service import create_parent,update_parent
    with auth.app.app_context():
        admin=actor(auth);data={**STUDENT_DATA,'class_id':None};student=create_student(admin,data)
        update_student(admin,student.student_id,{**data,'name':'更新档案'})
        change_student_status(admin,student.student_id,'suspended');set_student_archived(admin,student.student_id,True);set_student_archived(admin,student.student_id,False)
        teacher=create_teacher(admin,TEACHER_DATA);update_teacher(admin,teacher.teacher_id,{**TEACHER_DATA,'name':'更新教师'})
        school_class=create_class(admin,{**CLASS_DATA,'homeroom_teacher_id':None});update_class(admin,school_class.class_id,{**CLASS_DATA,'homeroom_teacher_id':teacher.teacher_id})
        parent=create_parent(admin,student.student_id,PARENT_DATA);update_parent(admin,student.student_id,parent.parent_id,{**PARENT_DATA,'name':'更新监护人'})
        db.session.flush();logs=db.session.scalars(select(AuditLog)).all()
        assert len(logs)==11
        assert {a.action for a in logs}=={'create','update','status_change','archive','restore'}
        assert all(a.actor_user_id==admin.user_id and a.created_at is not None for a in logs)
        assert all('password_hash' not in str(a.after_data) for a in logs)
        db.session.rollback()
        assert db.session.scalar(select(Student).where(Student.student_no=='CRUD-S1')) is None
        assert db.session.scalar(select(AuditLog)) is None


@pytest.mark.parametrize('failure',['audit','student'])
def test_real_database_failure_rolls_back_business_and_audit(auth,failure,caplog):
    from app.extensions import db
    from app.models import Student,AuditLog
    with auth.app.app_context():
        table='audit_logs' if failure=='audit' else 'students'
        db.session.execute(text(f"CREATE TRIGGER simulated_failure BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT, 'private-storage-error'); END"));db.session.commit()
    auth.login();response=submit(auth,'/admin/students/new',STUDENT_DATA)
    assert response.status_code in (409,503)
    assert 'private-storage-error' not in response.text+caplog.text
    with auth.app.app_context():
        assert db.session.scalar(select(Student).where(Student.student_no=='CRUD-S1')) is None
        assert db.session.scalar(select(AuditLog)) is None


def test_primary_switch_audits_both_and_later_failure_restores_original(auth):
    from app.extensions import db
    from app.models import Parent,AuditLog
    from app.services.parent_service import create_parent,set_primary_parent
    with auth.app.app_context():
        admin=actor(auth);sid=auth.student_ids[0]
        first=create_parent(admin,sid,{**PARENT_DATA,'is_primary':True});second=create_parent(admin,sid,{**PARENT_DATA,'name':'第二位'})
        db.session.commit();first_id=first.parent_id;second_id=second.parent_id
        set_primary_parent(admin,sid,second_id);db.session.commit()
        assert not first.is_primary and second.is_primary
        logs=db.session.scalars(select(AuditLog).where(AuditLog.action=='update')).all()
        assert {a.entity_id for a in logs}=={first_id,second_id}
        db.session.execute(text("CREATE TRIGGER audit_fail BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT,'fail'); END"));db.session.commit()
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            set_primary_parent(admin,sid,first_id);db.session.flush()
        db.session.rollback()
        assert not db.session.get(Parent,first_id).is_primary and db.session.get(Parent,second_id).is_primary


@pytest.mark.parametrize('domain',['student','teacher','class','parent'])
def test_audit_failure_reverts_existing_profile_edit_for_every_domain(auth,domain):
    from app.extensions import db
    from app.models import Student,Teacher,SchoolClass,Parent,AuditLog
    from app.services.class_service import create_class
    from app.services.parent_service import create_parent
    auth.login()
    with auth.app.app_context():
        if domain=='student':
            row=db.session.get(Student,auth.student_ids[0]);path=f'/admin/students/{row.student_id}/edit';data={**STUDENT_DATA,'student_no':row.student_no}
        elif domain=='teacher':
            row=db.session.scalar(select(Teacher));path=f'/admin/teachers/{row.teacher_id}/edit';data={**TEACHER_DATA,'teacher_no':row.teacher_no}
        elif domain=='class':
            row=create_class(actor(auth),{**CLASS_DATA,'homeroom_teacher_id':None});db.session.commit();path=f'/admin/classes/{row.class_id}/edit';data={**CLASS_DATA,'class_name':'将被回滚的班级名'}
        else:
            row=create_parent(actor(auth),auth.student_ids[0],PARENT_DATA);db.session.commit();path=f'/admin/students/{row.student_id}/parents/{row.parent_id}/edit';data={**PARENT_DATA,'name':'将被回滚的家长名'}
        model=type(row);pk=next(iter(row.__table__.primary_key.columns)).key;identity=getattr(row,pk)
        original={c.name:getattr(row,c.name) for c in row.__table__.columns}
        count=len(db.session.scalars(select(AuditLog)).all())
        db.session.execute(text("CREATE TRIGGER audit_fail_edit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT,'private-edit-error'); END"));db.session.commit()
    assert submit(auth,path,data).status_code==409
    with auth.app.app_context():
        row=db.session.get(model,identity)
        assert {c.name:getattr(row,c.name) for c in row.__table__.columns}==original
        assert len(db.session.scalars(select(AuditLog)).all())==count


def test_stale_independent_session_cannot_reverse_terminal_student_state(auth,monkeypatch):
    from sqlalchemy.orm import Session
    from app.extensions import db
    from app.models import Student,User,AuditLog
    from app.services.student_service import change_student_status
    with auth.app.app_context():
        with Session(db.engine) as a,Session(db.engine) as b:
            admin_a=a.get(User,auth.ids['auth_admin']);student_a=a.get(Student,auth.student_ids[0])
            assert student_a.status=='enrolled'
            with monkeypatch.context() as patch:
                patch.setattr(db,'session',b)
                change_student_status(b.get(User,auth.ids['auth_admin']),student_a.student_id,'graduated');b.commit()
            with monkeypatch.context() as patch:
                patch.setattr(db,'session',a)
                with pytest.raises(ValueError):change_student_status(admin_a,student_a.student_id,'suspended')
                a.rollback()
            db.session.expire_all()
            assert db.session.get(Student,student_a.student_id).status=='graduated'
            logs=db.session.scalars(select(AuditLog).where(AuditLog.action=='status_change')).all()
            assert len(logs)==1 and logs[0].after_data['status']=='graduated'


def test_stale_independent_session_primary_switch_takes_effect(auth,monkeypatch):
    from sqlalchemy.orm import Session
    from app.extensions import db
    from app.models import Parent,User
    from app.services.parent_service import create_parent,set_primary_parent
    with auth.app.app_context():
        first=create_parent(actor(auth),auth.student_ids[0],{**PARENT_DATA,'is_primary':True})
        second=create_parent(actor(auth),auth.student_ids[0],{**PARENT_DATA,'name':'另一位'})
        db.session.commit();first_id=first.parent_id;second_id=second.parent_id
        with Session(db.engine) as a,Session(db.engine) as b:
            admin_a=a.get(User,auth.ids['auth_admin']);cached_first=a.get(Parent,first_id)
            assert cached_first.is_primary
            with monkeypatch.context() as patch:
                patch.setattr(db,'session',b)
                set_primary_parent(b.get(User,auth.ids['auth_admin']),auth.student_ids[0],second_id);b.commit()
            with monkeypatch.context() as patch:
                patch.setattr(db,'session',a)
                set_primary_parent(admin_a,auth.student_ids[0],first_id);a.commit()
            db.session.expire_all()
            assert db.session.get(Parent,first_id).is_primary and not db.session.get(Parent,second_id).is_primary
