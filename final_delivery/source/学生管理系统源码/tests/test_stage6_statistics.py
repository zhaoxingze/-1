from decimal import Decimal

from app.extensions import db
from student_records_support import ATTENDANCE, actor, scoped_teacher, student_records


def test_attendance_statistics_use_scope_and_exclude_leave(student_records):
    from app.services.attendance_service import attendance_statistics, create_attendance

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth)
        for index, status in enumerate(("present", "late", "absent", "leave")):
            create_attendance(operator, ids.own, {**ATTENDANCE, "period": f"测试{index}", "status": status})
        counts, rate = attendance_statistics(operator, start="2026-11-19", end="2026-11-19")
        assert counts == {"present": 1, "late": 1, "absent": 1, "leave": 1} and rate == Decimal("66.67")
        counts, rate = attendance_statistics(operator, end="2026-11-18")
        assert sum(counts.values()) == 0 and rate is None


def test_stats_show_no_data_with_empty_or_leave_only_records(student_records):
    from app.services.attendance_service import create_attendance

    auth, ids = student_records.auth, student_records.ids
    path = "/attendance/statistics"
    assert "无可统计数据" in auth.client.get(path).text
    with auth.app.app_context():
        create_attendance(actor(auth), ids.own, {**ATTENDANCE, "status": "leave"})
        db.session.commit()
    page = auth.client.get(path)
    assert page.status_code == 200 and "无可统计数据" in page.text
    assert "0.00%" not in page.text and "100.00%" not in page.text
