import pytest

from app.extensions import db
from app.models import Course
from academics_support import academic, scoped_teacher, PAST, TERM, sign_in
from archive_support import submit


@pytest.mark.parametrize("endpoint", ["/academics/courses", "/academics/enrollments", "/academics/grades", "/academics/grades/1/edit"])
def test_anonymous_get_redirects_to_login(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 302 and response.location.startswith("/login")


def test_student_can_read_own_history_but_not_other_records_or_write(academic):
    sign_in(academic, "auth_student")
    auth = academic.auth
    page = auth.client.get("/academics/grades?semester=")
    assert page.status_code == 200 and "87.00" in page.text and PAST in page.text
    assert "AUTH-S2" not in page.text
    assert auth.client.get(f"/academics/grades?student_id={academic.ids.course_only}").status_code == 403
    assert auth.client.get(f"/academics/grades/{academic.current}/edit").status_code == 403
    assert auth.client.get("/academics/enrollments/new").status_code == 403
    token = auth.token("/profile")
    assert auth.client.post("/academics/enrollments/new", data={"csrf_token": token, "course_id": 1, "student_id": 1, "semester": TERM}).status_code == 403


def test_forged_form_parameters_and_missing_csrf_cannot_change_grade(academic):
    auth = academic.auth
    path = f"/academics/grades/{academic.current}/edit"
    assert auth.client.post(path, data={"usual_score": 80, "exam_score": 90}).status_code == 400
    for key in ("course_id", "student_id", "teacher_id", "semester", "actor_user_id", "total_score"):
        assert submit(auth, path, {"usual_score": "80", "exam_score": "90", key: "1"}).status_code == 400


def test_forged_enrollment_values_still_require_a22(academic):
    auth, ids = academic.auth, academic.ids
    path = "/academics/enrollments/new"
    valid = {"course_id": ids.own_course, "student_id": ids.own, "semester": TERM}
    for overrides in ({"course_id": ids.other_course}, {"student_id": ids.unrelated}, {"semester": PAST}):
        assert submit(auth, path, {**valid, **overrides}).status_code == 403
    assert submit(auth, path, {**valid, "teacher_id": ids.other_teacher}).status_code == 400


def test_reassigned_course_revokes_previously_open_form(academic):
    auth = academic.auth
    path = f"/academics/grades/{academic.current}/edit"
    token = auth.token(path)
    with auth.app.app_context():
        db.session.get(Course, academic.ids.own_course).teacher_id = academic.ids.other_teacher
        db.session.commit()
    assert auth.client.post(path, data={"csrf_token": token, "usual_score": "80", "exam_score": "90"}).status_code == 403


def test_scoped_aggregates_and_pagination(academic):
    auth, ids = academic.auth, academic.ids
    page = auth.client.get(f"/academics/grades?semester={TERM}&per_page=1")
    assert page.status_code == 200 and "共 1 条" in page.text
    assert "AUTH-S2" in page.text and "范围外学生" not in page.text
    assert auth.client.get(f"/academics/grades?semester={PAST}").status_code == 403
    assert auth.client.get(f"/academics/courses/{ids.other_course}").status_code == 403
    page_two = auth.client.get(f"/academics/grades?semester={TERM}&per_page=1&page=2")
    assert page_two.status_code == 404
    assert auth.client.get(f"/academics/courses/{ids.own_course}?semester={TERM}").status_code == 200
