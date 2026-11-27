from datetime import date

from app.extensions import db
from app.models import AttendanceRecord
from archive_support import submit
from student_records_support import ATTENDANCE, actor, scoped_teacher, sign_in, student_records


def test_attendance_create_edit_and_date_filters(student_records):
    auth, ids = student_records.auth, student_records.ids
    data = {**ATTENDANCE, "student_id": ids.own, "attendance_date": "2026-11-19"}
    created = submit(auth, "/attendance/new", data)
    assert created.status_code == 303
    detail = auth.client.get(created.location)
    assert detail.status_code == 200 and "课间集合" in detail.text
    data.pop("student_id")
    sign_in(auth, "auth_admin")
    edited = submit(auth, created.location + "/edit", {**data, "status": "late"})
    assert edited.status_code == 303 and "迟到" in auth.client.get(edited.location).text
    page = auth.client.get(f"/attendance/?class_id={ids.own_class}&start=2026-11-19&end=2026-11-19")
    assert page.status_code == 200 and "AUTH-S1" in page.text and "AUTH-S2" not in page.text
    with auth.app.app_context():
        row = db.session.get(AttendanceRecord, int(created.location.split("/")[-1]))
        assert row.attendance_date == date(2026, 11, 19) and row.recorded_by == auth.ids["auth_admin"]


def test_student_reads_only_own_attendance(student_records):
    from app.services.attendance_service import create_attendance

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        row = create_attendance(actor(auth), ids.own, ATTENDANCE)
        db.session.commit()
        identity = row.attendance_id
    sign_in(auth, "auth_student")
    page = auth.client.get("/attendance/")
    assert page.status_code == 200 and "AUTH-S1" in page.text and "AUTH-S2" not in page.text
    assert auth.client.get(f"/attendance/{identity}").status_code == 200
    assert auth.client.get(f"/attendance/{identity}/edit").status_code == 403
    assert auth.client.get(f"/attendance/{ids.other_attendance}").status_code == 403
    assert auth.client.get(f"/attendance/?student_id={ids.course_only}").status_code == 403
