import pytest

from archive_support import STUDENT_DATA, submit
from teacher_scope_support import scoped_teacher


@pytest.mark.parametrize("path", [
    "/teacher/classes", "/teacher/courses", "/teacher/classes/1/students",
    "/teacher/courses/1/students", "/teacher/students/1",
    "/teacher/students/1/contact", "/teacher/students/1/parents",
])
def test_anonymous_must_log_in(client, path):
    response = client.get(path)
    assert response.status_code == 302 and response.location.startswith("/login?next=")


def test_id_changes_and_forged_scope_do_not_extend_permissions(scoped_teacher):
    auth, ids = scoped_teacher
    token = auth.token(f"/teacher/students/{ids.own}/contact")
    for candidate in (ids.course_only, ids.unrelated, 9223372036854775808):
        path = f"/teacher/students/{candidate}/contact"
        assert auth.client.get(path).status_code == 403
        response = auth.client.post(path, data={"csrf_token": token, "phone": "000-4999",
                                              "teacher_id": ids.other_teacher, "class_id": ids.own_class})
        assert response.status_code == 403
    assert auth.client.get(f"/teacher/classes/{ids.other_class}/students?teacher_id={ids.other_teacher}&role_id=17").status_code == 403
    assert auth.client.get("/admin/students/new").status_code == 403


def test_student_scope_and_admin_archive_creation_remain_intact(auth):
    auth.login("auth_student")
    own, other = auth.student_ids
    assert auth.client.get(f"/students/{own}/profile").status_code == 200
    assert auth.client.get(f"/students/{other}/profile").status_code == 403
    assert auth.client.get("/teacher/classes").status_code == 403
    auth.client.post("/logout", data={"csrf_token": auth.token("/profile")})
    assert auth.login().status_code == 303
    assert submit(auth, "/admin/students/new", STUDENT_DATA).status_code == 303
