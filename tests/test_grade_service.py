from decimal import Decimal

import pytest

from app.extensions import db
from academics_support import academic, scoped_teacher, actor


@pytest.mark.parametrize("usual,exam,expected", [
    (80, 90, "87.00"), (0, 100, "70.00"), (100, 0, "30.00"),
    (Decimal("0.05"), Decimal("0"), "0.02"),
])
def test_total_uses_decimal_half_up(usual, exam, expected):
    from app.services.grade_service import calculate_total

    result = calculate_total(usual, exam)
    assert isinstance(result, Decimal) and str(result) == expected


@pytest.mark.parametrize("value", [-1, 101, Decimal("NaN"), float("inf"), "80", "bad", None, False])
def test_invalid_or_missing_grade_is_rejected(value):
    from app.services.grade_service import calculate_total

    with pytest.raises(ValueError):
        calculate_total(value, 90)
    with pytest.raises(ValueError):
        calculate_total(80, value)


def test_teacher_grade_scope_is_own_course_and_current_term_not_homeroom(academic):
    from app.services.grade_service import save_grades

    with academic.auth.app.app_context():
        row = save_grades(actor(academic), academic.current, 80, 90)
        db.session.commit()
        assert row.total_score == 87 and row.student_id == academic.ids.course_only
        for identity in (academic.past, academic.other, 999999):
            with pytest.raises(PermissionError):
                save_grades(actor(academic), identity, 80, 90)
            db.session.rollback()
        past = save_grades(actor(academic, "auth_admin"), academic.past, 100, 100)
        assert past.total_score == 100
        db.session.rollback()
