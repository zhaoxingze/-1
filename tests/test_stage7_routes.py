import pytest

from archive_support import submit
from stage7_support import create_fields, dashboard_data, scoped_teacher
from student_records_support import sign_in


@pytest.mark.parametrize("username,path", [("auth_admin", "/admin/"), ("auth_teacher", "/dashboard/teacher"),
                                           ("auth_student", "/dashboard/student")])
def test_workbench_and_shared_navigation_render_only_available_actions(dashboard_data, username, path):
    auth, _ = dashboard_data
    sign_in(auth, username)
    response = auth.client.get(path)
    assert response.status_code == 200
    html = response.text
    assert 'id="primary-navigation"' in html and "功能菜单" in html
    assert "首页统计" in html and "待开发" not in html
    assert 'href="/attendance/"' in html
    if username == "auth_admin":
        for target in ("/admin/students", "/admin/teachers", "/admin/classes", "/admin/parents",
                       "/academics/courses", "/academics/enrollments", "/academics/grades", "/records/rewards",
                       "/records/contacts", "/records/notifications", "/admin/users", "/admin/audit"):
            assert f'href="{target}"' in html and auth.client.get(target).status_code == 200
    else:
        assert 'href="/admin/users"' not in html and 'href="/admin/audit"' not in html
    if username == "auth_student":
        assert 'href="/records/rewards"' not in html and 'href="/records/contacts"' not in html


def test_course_teacher_without_homeroom_has_course_navigation_only(auth):
    auth.login("auth_teacher")
    html = auth.client.get("/dashboard/teacher").text
    assert 'href="/teacher/courses"' in html and 'href="/academics/grades"' in html
    assert 'href="/attendance/"' not in html and 'href="/records/notifications"' not in html


def test_account_form_requires_explicit_role_and_success_feedback(auth):
    auth.login()
    path = "/admin/users/new"
    page = auth.client.get(path)
    assert page.status_code == 200 and "请选择角色" in page.text
    response = submit(auth, path, create_fields())
    assert response.status_code == 303
    assert "alert-success" in auth.client.get(response.location).text
