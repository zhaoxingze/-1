import pytest

from app.extensions import db
from app.models import Enrollment
from academics_support import academic, scoped_teacher, PAST, TERM, sign_in
from archive_support import submit


def test_teacher_adds_enrollment_and_saves_grade_from_browser_forms(academic):
    auth, ids = academic.auth, academic.ids
    created = submit(auth, "/academics/enrollments/new", {
        "student_id": ids.own, "course_id": ids.own_course, "semester": TERM,
    })
    assert created.status_code == 303
    assert "AUTH-S1" in auth.client.get(created.location).text
    path = f"/academics/grades/{academic.current}/edit"
    for data in ({"usual_score": "80"}, {"usual_score": "bad", "exam_score": "90"},
                 {"usual_score": "NaN", "exam_score": "90"}, {"usual_score": "101", "exam_score": "90"}):
        assert submit(auth, path, data).status_code == 200
    saved = submit(auth, path, {"usual_score": "80", "exam_score": "90"})
    assert saved.status_code == 303
    assert "87.00" in auth.client.get(saved.location).text
    with auth.app.app_context():
        assert db.session.get(Enrollment, academic.current).total_score == 87


def test_enrollment_and_grade_views_filter_by_semester_and_student(academic):
    sign_in(academic, "auth_admin")
    auth, ids = academic.auth, academic.ids
    page = auth.client.get(f"/academics/enrollments?semester={PAST}&course_id={ids.own_course}")
    assert page.status_code == 200 and "AUTH-S1" in page.text and "AUTH-S2" not in page.text
    page = auth.client.get(f"/academics/grades?semester={TERM}&student_id={ids.course_only}")
    assert page.status_code == 200 and "未评分" in page.text and "AUTH-S1" not in page.text


def test_pagination_links_keep_semester_course_and_search(academic):
    auth, ids = academic.auth, academic.ids
    page = auth.client.get(f"/academics/enrollments?semester=&course_id={ids.own_course}&q=AUTH-S&per_page=1")
    assert page.status_code == 200 and "下一页" in page.text
    from html import unescape
    from re import search

    link = unescape(search(r'href="([^"]+)">下一页', page.text)[1])
    assert "semester=" in link and f"course_id={ids.own_course}" in link and "q=AUTH-S" in link
    assert auth.client.get(link).status_code == 200


def test_active_semester_can_be_overridden_by_environment(monkeypatch, tmp_path):
    from app import create_app

    monkeypatch.setenv("ACTIVE_SEMESTER", "EXPLICIT-TERM")
    assert create_app(instance_path=str(tmp_path / "dev")).config["ACTIVE_SEMESTER"] == "EXPLICIT-TERM"
    assert create_app("testing", {"ACTIVE_SEMESTER": "TEST-TERM"}, instance_path=str(tmp_path / "test")).config["ACTIVE_SEMESTER"] == "TEST-TERM"
