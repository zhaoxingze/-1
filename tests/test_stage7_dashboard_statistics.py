from datetime import date
from decimal import Decimal

import pytest

from stage7_support import CURRENT, PAST, TODAY, actor, dashboard_data, scoped_teacher


def test_admin_counts_all_profiles_but_active_enrolled_matches_both_flags(dashboard_data):
    from app.services.dashboard_statistics_service import admin_statistics

    auth, ids = dashboard_data
    with auth.app.app_context():
        stats = admin_statistics(actor(auth))
        assert stats["counts"] == {"students": 3, "enrolled": 1, "archived": 1, "teachers": 2, "classes": 2, "courses": 2}
        assert stats["semester"] == CURRENT
        assert stats["averages"] == {ids.own_course: (2, 90.0), ids.other_course: (1, 20.0)}


def test_complete_scores_are_filtered_by_selected_semester(dashboard_data):
    from app.services.dashboard_statistics_service import admin_statistics

    auth, ids = dashboard_data
    with auth.app.app_context():
        stats = admin_statistics(actor(auth), semester=PAST)
        assert stats["averages"] == {ids.own_course: (1, 42.0)}
        assert ids.other_course not in stats["averages"]


def test_utc_boundary_and_attendance_rate_exclude_leave(dashboard_data):
    from app.services.dashboard_statistics_service import admin_statistics

    auth, ids = dashboard_data
    with auth.app.app_context():
        stats = admin_statistics(actor(auth))
        assert stats["start"] == date(2026, 10, 21) and stats["end"] == TODAY
        assert stats["attendance"] == {"present": 1, "late": 1, "absent": 1, "leave": 1}
        assert stats["rate"] == Decimal("66.67")
        scoped = admin_statistics(actor(auth), class_id=ids.own_class)
        assert scoped["attendance"] == {"present": 0, "late": 1, "absent": 0, "leave": 1}
        assert scoped["rate"] == Decimal("100.00")


@pytest.mark.parametrize("term", ["", "Z" * 31, "2026-Wrong"])
def test_dashboard_rejects_invalid_or_unlisted_semester(dashboard_data, term):
    from urllib.parse import urlencode
    from student_records_support import sign_in

    auth, _ = dashboard_data
    sign_in(auth, "auth_admin")
    assert auth.client.get("/admin/?" + urlencode({"semester": term})).status_code == 400


def test_no_completed_grades_are_shown_as_no_data(dashboard_data):
    from student_records_support import sign_in

    auth, _ = dashboard_data
    sign_in(auth, "auth_admin")
    page = auth.client.get(f"/admin/?semester={PAST}")
    assert page.status_code == 200 and "42.00" in page.text and "暂无数据" in page.text
