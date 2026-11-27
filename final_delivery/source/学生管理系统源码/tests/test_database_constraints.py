"""SQLite and ORM integrity, including paths bypassing ordinary setters."""

from datetime import date

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def graph(test_db):
    from app.models import Course, Parent, Role, Student, Teacher, User

    role = Role(name="admin")
    admin = User(username="admin", password_hash="hash", role=role)
    teacher = Teacher(teacher_no="T1", name="Teacher")
    one = Student(student_no="S1", name="One", gender="X", enrollment_date=date(2026, 9, 1))
    two = Student(student_no="S2", name="Two", gender="X", enrollment_date=date(2026, 9, 1))
    course = Course(course_code="C1", course_name="Course", credit=1.0, teacher=teacher)
    parent = Parent(student=one, name="Guardian", relationship="guardian", phone="000", is_primary=True)
    test_db.session.add_all([admin, teacher, one, two, course, parent])
    test_db.session.commit()
    return dict(admin=admin, teacher=teacher, one=one, two=two, course=course, parent=parent)


def test_foreign_keys_are_enabled(test_db):
    assert test_db.session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


@pytest.mark.parametrize("kind", ["username", "student_no", "teacher_no", "course_code", "enrollment", "attendance"])
def test_duplicate_identifiers_and_records_are_rejected(test_db, graph, kind):
    from app.models import AttendanceRecord, Course, Enrollment, Student, Teacher, User

    if kind == "username":
        objects = [User(username="admin", password_hash="hash", role=graph["admin"].role)]
    elif kind == "student_no":
        objects = [Student(student_no="S1", name="Duplicate", gender="X", enrollment_date=date(2026, 9, 1))]
    elif kind == "teacher_no":
        objects = [Teacher(teacher_no="T1", name="Duplicate")]
    elif kind == "course_code":
        objects = [Course(course_code="C1", course_name="Duplicate", credit=1)]
    elif kind == "enrollment":
        objects = [Enrollment(student=graph["one"], course=graph["course"], semester="2026-Fall") for _ in range(2)]
    else:
        objects = [AttendanceRecord(student=graph["one"], attendance_date=date(2026, 11, 16), period="1", status="present", recorder=graph["admin"]) for _ in range(2)]
    test_db.session.add_all(objects)
    with pytest.raises(IntegrityError):
        test_db.session.flush()
    test_db.session.rollback()
    assert test_db.session.get(User, graph["admin"].user_id).username == "admin"


@pytest.mark.parametrize("column,value", [("usual_score", -1), ("exam_score", 101), ("total_score", -1)])
def test_score_check_rejects_raw_sql(test_db, graph, column, value):
    with pytest.raises(IntegrityError):
        test_db.session.execute(text(f"INSERT INTO enrollments (student_id,course_id,semester,{column},created_at) VALUES (:student,:course,'2026-Fall',:score,CURRENT_TIMESTAMP)"), {"student": graph["one"].student_id, "course": graph["course"].course_id, "score": value})
    test_db.session.rollback()


@pytest.mark.parametrize("table,sql,parameters", [
    ("attendance", "INSERT INTO attendance_records (student_id,attendance_date,period,status,recorded_by) VALUES (:student,'2026-11-16','1','invalid',:actor)", {}),
    ("reward", "INSERT INTO reward_records (student_id,record_type,category,description,occurred_on,created_by) VALUES (:student,'invalid','other','x','2026-11-16',:actor)", {}),
    ("student", "UPDATE students SET status='invalid' WHERE student_id=:student", {}),
    ("parent", "UPDATE parents SET relationship='invalid' WHERE parent_id=:parent", {}),
    ("contact", "INSERT INTO parent_contact_logs (student_id,parent_id,method,content,contacted_at,created_by) VALUES (:student,:parent,'invalid','x',CURRENT_TIMESTAMP,:actor)", {}),
    ("notification", "INSERT INTO notification_logs (student_id,channel,recipient_snapshot,content,status,created_by,created_at) VALUES (:student,'fax','{}','x','simulated',:actor,CURRENT_TIMESTAMP)", {}),
    ("bool", "UPDATE students SET is_archived=2 WHERE student_id=:student", {}),
    ("fk", "UPDATE students SET class_id=999999 WHERE student_id=:student", {}),
])
def test_database_checks_and_foreign_keys(test_db, graph, table, sql, parameters):
    parameters.update(student=graph["one"].student_id, parent=graph["parent"].parent_id, actor=graph["admin"].user_id)
    with pytest.raises(IntegrityError):
        test_db.session.execute(text(sql), parameters)
    test_db.session.rollback()


def test_only_one_primary_parent_per_student(test_db, graph):
    from app.models import Parent

    test_db.session.add(Parent(student=graph["one"], name="Second", relationship="other", phone="001", is_primary=True))
    with pytest.raises(IntegrityError):
        test_db.session.flush()
    test_db.session.rollback()
    test_db.session.add(Parent(student=graph["one"], name="Additional", relationship="other", phone="002", is_primary=False))
    test_db.session.commit()


def test_orm_deletion_does_not_null_out_optional_history(test_db, graph):
    from app.models import ParentContactLog

    log = ParentContactLog(student=graph["one"], parent=graph["parent"], method="phone", content="history", creator=graph["admin"])
    test_db.session.add(log)
    test_db.session.commit()
    # Force the loaded-parent case that SQLAlchemy otherwise nulls out.
    assert graph["parent"].contact_logs == [log]
    test_db.session.delete(graph["parent"])
    with pytest.raises(IntegrityError):
        test_db.session.flush()
    test_db.session.rollback()
    assert log.parent_id == graph["parent"].parent_id


def test_student_history_prevents_delete_and_transaction_recovers(test_db, graph):
    from app.models import Student

    student_id = graph["one"].student_id
    assert graph["one"].parents
    test_db.session.delete(graph["one"])
    with pytest.raises(IntegrityError):
        test_db.session.flush()
    test_db.session.rollback()
    assert test_db.session.get(Student, student_id) is not None


@pytest.mark.parametrize("model_name", ["ParentContactLog", "NotificationLog"])
def test_orm_parent_must_belong_to_student(test_db, graph, model_name):
    from app import models

    fields = dict(student=graph["two"], parent=graph["parent"], content="x", creator=graph["admin"])
    fields.update(method="phone") if model_name == "ParentContactLog" else fields.update(channel="sms", status="simulated", recipient_snapshot={"phone": "000"})
    test_db.session.add(getattr(models, model_name)(**fields))
    with pytest.raises(ValueError):
        test_db.session.flush()
    test_db.session.rollback()


@pytest.mark.parametrize("table", ["parent_contact_logs", "notification_logs"])
def test_raw_parent_mismatch_insert_and_update_are_rejected(test_db, graph, table):
    params = dict(student=graph["two"].student_id, parent=graph["parent"].parent_id, actor=graph["admin"].user_id)
    if table == "parent_contact_logs":
        sql = "INSERT INTO parent_contact_logs (student_id,parent_id,method,content,contacted_at,created_by) VALUES (:student,:parent,'phone','x',CURRENT_TIMESTAMP,:actor)"
    else:
        sql = "INSERT INTO notification_logs (student_id,parent_id,channel,recipient_snapshot,content,status,created_by,created_at) VALUES (:student,:parent,'sms','{}','x','simulated',:actor,CURRENT_TIMESTAMP)"
    with pytest.raises(IntegrityError):
        test_db.session.execute(text(sql), params)
    test_db.session.rollback()
    params["student"] = graph["one"].student_id
    test_db.session.execute(text(sql), params)
    test_db.session.commit()
    with pytest.raises(IntegrityError):
        test_db.session.execute(text(f"UPDATE {table} SET student_id=:student"), {"student": graph["two"].student_id})
    test_db.session.rollback()


@pytest.mark.parametrize("name", [None, "", " \t\n "])
def test_contact_without_parent_requires_nonblank_name(test_db, graph, name):
    from app.models import ParentContactLog

    log = ParentContactLog(student=graph["one"], method="phone", content="x", creator=graph["admin"], contact_person_name=name)
    test_db.session.add(log)
    with pytest.raises((ValueError, IntegrityError)):
        test_db.session.flush()
    test_db.session.rollback()


def test_optional_parent_relationship_can_be_cleared_without_stale_fk_error(test_db, graph):
    from app.models import ParentContactLog

    log = ParentContactLog(student=graph["one"], parent=graph["parent"], method="phone", content="x", creator=graph["admin"])
    test_db.session.add(log)
    test_db.session.commit()
    assert log.parent is graph["parent"]
    log.parent = None
    log.contact_person_name = "Independent contact"
    test_db.session.commit()
    assert log.parent_id is None


def test_pending_contact_and_notification_graphs_can_be_flushed(test_db):
    from app.models import NotificationLog, Parent, ParentContactLog, Role, Student, User

    student = Student(student_no="pending", name="Pending", gender="X", enrollment_date=date(2026, 9, 1))
    parent = Parent(student=student, name="Parent", relationship="other", phone="000")
    admin = User(username="pending-admin", password_hash="hash", role=Role(name="admin"))
    contact = ParentContactLog(student=student, parent=parent, method="phone", content="x", creator=admin)
    notification = NotificationLog(student=student, parent=parent, channel="sms", content="x", recipient_snapshot={"phone": "000"}, creator=admin, status="simulated")
    test_db.session.add_all([contact, notification])
    test_db.session.commit()
    assert contact.student_id == notification.student_id == parent.student_id
    assert contact.parent_id == notification.parent_id == parent.parent_id


@pytest.mark.parametrize("path", ["contact_fk", "notification_fk", "parent_raw"])
def test_changing_existing_links_cannot_create_cross_student_history(test_db, graph, path):
    from app.models import NotificationLog, ParentContactLog

    contact = ParentContactLog(student=graph["one"], parent=graph["parent"], method="phone", content="x", creator=graph["admin"])
    notification = NotificationLog(student=graph["one"], parent=graph["parent"], channel="sms", content="x", recipient_snapshot={"phone": "000"}, creator=graph["admin"], status="simulated")
    test_db.session.add_all([contact, notification])
    test_db.session.commit()
    with pytest.raises((ValueError, IntegrityError)):
        if path == "parent_raw":
            test_db.session.execute(text("UPDATE parents SET student_id=:student WHERE parent_id=:parent"), {"student": graph["two"].student_id, "parent": graph["parent"].parent_id})
        else:
            record = contact if path == "contact_fk" else notification
            assert record.student is graph["one"]
            record.student_id = graph["two"].student_id
            test_db.session.flush()
    test_db.session.rollback()


@pytest.mark.parametrize("role_name,binding", [("admin", "teacher"), ("admin", "student"), ("teacher", "student"), ("student", "teacher"), ("teacher", None), ("student", None)])
def test_orm_flush_validates_user_role_and_profile(test_db, graph, role_name, binding):
    from app.models import Role, User

    role = graph["admin"].role if role_name == "admin" else Role(name=role_name)
    user = User(username="invalid-profile", password_hash="hash", role=role)
    if binding is not None:
        setattr(user, binding, graph["teacher" if binding == "teacher" else "one"])
    test_db.session.add(user)
    with pytest.raises(ValueError):
        test_db.session.flush()
    test_db.session.rollback()


@pytest.mark.parametrize("path", ["orm_update", "orm_delete", "bulk_update", "bulk_delete", "raw_update", "raw_delete"])
def test_audit_is_append_only_on_all_write_paths(test_db, path):
    from app.models import AuditLog

    log = AuditLog(entity_type="student", entity_id=1, action="create")
    test_db.session.add(log)
    test_db.session.commit()
    with pytest.raises((ValueError, IntegrityError)):
        if path == "orm_update":
            log.action = "update"
            test_db.session.flush()
        elif path == "orm_delete":
            test_db.session.delete(log)
            test_db.session.flush()
        elif path == "bulk_update":
            test_db.session.execute(update(AuditLog).values(action="update"))
        elif path == "bulk_delete":
            test_db.session.execute(delete(AuditLog))
        elif path == "raw_update":
            test_db.session.execute(text("UPDATE audit_logs SET action='update'"))
        else:
            test_db.session.execute(text("DELETE FROM audit_logs"))
    test_db.session.rollback()
    assert test_db.session.scalar(select(AuditLog.action)) == "create"
