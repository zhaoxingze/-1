import pytest

from sqlalchemy import update

from app.extensions import db
from app.models import Student
from archive_support import submit
from student_records_support import ATTENDANCE, REWARD, actor, scoped_teacher, sign_in, student_records


@pytest.mark.parametrize("path", ["/attendance/", "/attendance/statistics", "/records/rewards",
                                  "/records/contacts", "/records/notifications"])
def test_anonymous_redirect(client, path):
    assert client.get(path).status_code == 302


def test_course_only_binding_and_unknown_action_grant_no_access(student_records):
    from app.services.attendance_service import create_attendance
    from app.services.permission_service import student_record_access

    auth, ids = student_records.auth, student_records.ids
    sign_in(auth, "only_course")
    for path in ("/attendance/", "/attendance/new", "/records/rewards", "/records/contacts", "/records/notifications"):
        assert auth.client.get(path).status_code == 403
    assert 'href="/attendance/"' not in auth.client.get("/dashboard/teacher").text
    with auth.app.app_context():
        with pytest.raises(PermissionError):
            create_attendance(actor(auth, "only_course"), ids.own, ATTENDANCE)
        with pytest.raises(PermissionError):
            student_record_access(actor(auth, "auth_admin"), "unknown")


def test_cross_class_query_and_writes_denied(student_records):
    auth, ids = student_records.auth, student_records.ids
    for path in (f"/attendance/?class_id={ids.other_class}", f"/attendance/{ids.other_attendance}/edit",
                 f"/records/contacts/{ids.other_contact}", f"/records/contacts?parent_id={ids.other_parent}"):
        assert auth.client.get(path).status_code == 403
    for path, data in (("/attendance/new", ATTENDANCE), ("/records/rewards/new", REWARD)):
        assert submit(auth, path, {**data, "student_id": ids.course_only}).status_code == 403


def test_students_denied_records_and_writes(student_records):
    auth = student_records.auth
    sign_in(auth, "auth_student")
    for path in ("/attendance/new", "/records/rewards", "/records/contacts", "/records/notifications"):
        assert auth.client.get(path).status_code == 403


def test_csrf_and_forged_actor_or_object_fields(student_records):
    auth, ids = student_records.auth, student_records.ids
    path = "/attendance/new"
    data = {**ATTENDANCE, "student_id": ids.own}
    assert auth.client.post(path, data=data).status_code == 400
    for field in ("teacher_id", "recorded_by", "created_by", "class_id"):
        assert submit(auth, path, {**data, field: 1}).status_code == 400
    created = submit(auth, path, data)
    assert created.status_code == 303
    assert submit(auth, created.location + "/edit", data).status_code == 400


def test_transferred_student_revokes_previously_open_form(student_records):
    auth, ids = student_records.auth, student_records.ids
    created = submit(auth, "/attendance/new", {**ATTENDANCE, "student_id": ids.own})
    assert created.status_code == 303
    path = created.location + "/edit"
    token = auth.token(path)
    with auth.app.app_context():
        db.session.get(Student, ids.own).class_id = ids.other_class
        db.session.commit()
    assert auth.client.post(path, data={**ATTENDANCE, "csrf_token": token}).status_code == 403


def test_scoped_write_checks_sql_even_if_student_is_cached(student_records):
    from app.services.attendance_service import create_attendance, get_attendance, update_attendance

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth)
        row = create_attendance(operator, ids.own, ATTENDANCE)
        db.session.commit()
        row = get_attendance(operator, row.attendance_id)
        assert row.student.class_id == ids.own_class
        with db.engine.begin() as connection:
            connection.execute(update(Student).where(Student.student_id == ids.own).values(class_id=ids.other_class))
        with pytest.raises(PermissionError):
            update_attendance(operator, row.attendance_id, {**ATTENDANCE, "status": "absent"})


def test_attendance_scope_applies_before_pagination(student_records):
    auth, ids = student_records.auth, student_records.ids
    for period in ("节次一", "节次二"):
        assert submit(auth, "/attendance/new", {**ATTENDANCE, "student_id": ids.own, "period": period}).status_code == 303
    first = auth.client.get(f"/attendance/?per_page=1&class_id={ids.own_class}&start=2026-11-19")
    assert first.status_code == 200 and "共 2 条" in first.text and "下一页" in first.text
    assert "AUTH-S2" not in first.text
    assert auth.client.get("/attendance/?page=3&per_page=1").status_code == 404
