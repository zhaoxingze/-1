import pytest

from app.extensions import db
from student_records_support import ATTENDANCE, actor, scoped_teacher, student_records


@pytest.mark.parametrize("username", ["auth_admin", "auth_teacher"])
def test_create_attendance_records_current_actor_and_rejects_duplicate(student_records, username):
    from app.services.attendance_service import create_attendance

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth, username)
        row = create_attendance(operator, ids.own, ATTENDANCE)
        assert row.student_id == ids.own and row.recorded_by == operator.user_id
        db.session.commit()
        with pytest.raises(ValueError, match="已登记"):
            create_attendance(operator, ids.own, ATTENDANCE)


@pytest.mark.parametrize("change", [
    {"status": "invalid"}, {"attendance_date": None}, {"attendance_date": "2026-02-31"},
    {"period": ""}, {"period": " "}, {"period": "超" * 31}, {"recorded_by": 100},
])
def test_invalid_attendance_data_is_rejected(student_records, change):
    from app.services.attendance_service import create_attendance

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context(), pytest.raises(ValueError):
        create_attendance(actor(auth), ids.own, {**ATTENDANCE, **change})


def test_edit_cannot_duplicate_other_period(student_records):
    from app.services.attendance_service import create_attendance, update_attendance

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth)
        create_attendance(operator, ids.own, ATTENDANCE)
        row = create_attendance(operator, ids.own, {**ATTENDANCE, "period": "另一个节次"})
        with pytest.raises(ValueError, match="已登记"):
            update_attendance(operator, row.attendance_id, ATTENDANCE)
