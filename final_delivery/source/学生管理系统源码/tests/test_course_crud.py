from decimal import Decimal

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Course, Enrollment
from academics_support import academic, scoped_teacher, COURSE_DATA, actor, sign_in
from archive_support import submit


def test_admin_creates_and_searches_courses(academic):
    sign_in(academic, "auth_admin")
    auth = academic.auth
    response = submit(auth, "/academics/courses/new", {**COURSE_DATA, "teacher_id": str(academic.ids.teacher)})
    assert response.status_code == 303
    detail = auth.client.get(response.location)
    assert detail.status_code == 200 and "AC-C03" in detail.text
    results = auth.client.get("/academics/courses?q=AC-C03&per_page=1")
    assert "虚构新课程" in results.text and "SCOPE-C1" not in results.text


@pytest.mark.parametrize("change", [{"course_code": "SCOPE-C1"}, {"teacher_id": 999999}, {"credit": Decimal("NaN")}])
def test_course_rejects_duplicate_number_missing_teacher_and_nonfinite_credit(academic, change):
    from app.services.course_service import create_course

    with academic.auth.app.app_context():
        with pytest.raises(ValueError):
            create_course(actor(academic, "auth_admin"), {**COURSE_DATA, "teacher_id": None,
                          "credit": Decimal("2.5"), **change})
        db.session.rollback()
        assert len(db.session.scalars(select(Course)).all()) == 2


def test_reassignment_preserves_existing_records_and_scores(academic):
    sign_in(academic, "auth_admin")
    auth, ids = academic.auth, academic.ids
    response = submit(auth, f"/academics/courses/{ids.own_course}/edit", {
        "course_code": "SCOPE-C1", "course_name": "更新课程名", "credit": "3",
        "teacher_id": str(ids.other_teacher), "description": "虚构说明",
    })
    assert response.status_code == 303
    with auth.app.app_context():
        assert db.session.get(Course, ids.own_course).teacher_id == ids.other_teacher
        assert db.session.get(Enrollment, academic.past).total_score == 87
