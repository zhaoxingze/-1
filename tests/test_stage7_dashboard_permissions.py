import pytest

from stage7_support import PAST, actor, dashboard_data, scoped_teacher
from student_records_support import sign_in


def test_teacher_separates_current_homeroom_from_course_statistics(dashboard_data):
    from app.services.dashboard_statistics_service import teacher_statistics

    auth, ids = dashboard_data
    with auth.app.app_context():
        stats = teacher_statistics(actor(auth, "auth_teacher"))
        assert stats["counts"] == {"classes": 1, "students": 1, "courses": 1}
        assert stats["averages"] == {ids.own_course: (2, 90.0)}
        assert stats["attendance"] == {"present": 0, "late": 1, "absent": 0, "leave": 1}
    page = auth.client.get("/dashboard/teacher")
    assert page.status_code == 200 and "本教师课程" in page.text and "其他教师课程" not in page.text
    assert auth.client.get(f"/dashboard/teacher?class_id={ids.other_class}").status_code == 403
    assert auth.client.get(f"/dashboard/teacher?semester={PAST}").status_code == 403
    assert auth.client.get("/admin/").status_code == 403


def test_student_stats_come_only_from_authenticated_student(dashboard_data):
    from app.services.dashboard_statistics_service import student_statistics

    auth, ids = dashboard_data
    with auth.app.app_context():
        stats = student_statistics(actor(auth, "auth_student"))
        assert stats["student"].student_id == ids.own
        assert stats["counts"] == {"enrollments": 1, "completed": 1}
        assert stats["average"] == 84
        assert stats["attendance"]["late"] == 1 and stats["attendance"]["absent"] == 0
        with pytest.raises(PermissionError):
            student_statistics(actor(auth, "auth_teacher"))
    sign_in(auth, "auth_student")
    page = auth.client.get("/dashboard/student")
    assert page.status_code == 200 and "AUTH-S1" in page.text and "84.00" in page.text
    assert "AUTH-S2" not in page.text and "90.00" not in page.text
    assert auth.client.get(f"/dashboard/student?student_id={ids.course_only}").status_code == 403
    assert auth.client.get("/dashboard/teacher").status_code == 403
    assert auth.client.get("/admin/").status_code == 403
