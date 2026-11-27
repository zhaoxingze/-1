import pytest


@pytest.mark.parametrize("username", ["auth_admin", "auth_teacher", "auth_student"])
@pytest.mark.parametrize("role,path", [("admin", "/admin/"), ("teacher", "/dashboard/teacher"), ("student", "/dashboard/student")])
def test_workbench_role_matrix_uses_names(auth, username, role, path):
    auth.login(username)
    response = auth.client.get(path)
    assert response.status_code == (200 if username == f"auth_{role}" else 403)


@pytest.mark.parametrize("path", ["/admin/", "/dashboard", "/dashboard/teacher", "/dashboard/student", "/profile"])
def test_anonymous_requests_redirect_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.location.startswith("/login?next=")


def test_multi_role_decorator_and_student_rejection(auth):
    from app.services.permission_service import role_required
    @role_required("admin", "teacher")
    def shared(): return "authorized"
    auth.app.add_url_rule("/_test/shared", view_func=shared)
    auth.login("auth_teacher")
    assert auth.client.get("/_test/shared").status_code == 200
    auth.client.post("/logout", data={"csrf_token":auth.token("/profile")})
    auth.login("auth_student")
    assert auth.client.get("/_test/shared").status_code == 403
