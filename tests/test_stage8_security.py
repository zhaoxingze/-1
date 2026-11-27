import pytest

from app.extensions import db
from app.models import Student
from stage7_support import actor


@pytest.mark.parametrize("path", ["/", "/login", "/a-missing-page", "/static/css/app.css",
                                  "/static/vendor/bootstrap-5.3.3.min.css", "/health"])
def test_security_headers_cover_html_and_assets(client, path):
    response = client.get(path)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    if response.mimetype == "text/html":
        assert response.headers["Referrer-Policy"] == "same-origin"
        assert response.headers["X-Frame-Options"] == "DENY"
        policy = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in policy and "form-action 'self'" in policy
        assert "'unsafe-inline'" not in policy


def test_jinja_escapes_stored_labels_and_does_not_evaluate_template_syntax(auth):
    with auth.app.app_context():
        student = db.session.get(Student, auth.student_ids[0])
        student.name = "示例 <b>文本</b> {{ 6*7 }}"
        db.session.commit()
    auth.login()
    response = auth.client.get(f"/admin/students/{auth.student_ids[0]}")
    assert response.status_code == 200 and "&lt;b&gt;文本&lt;/b&gt; {{ 6*7 }}" in response.text
    assert "<b>文本</b>" not in response.text


def test_user_search_uses_literal_values_and_bounds(auth):
    auth.login()
    assert "共 0 条" in auth.client.get("/admin/users", query_string={"q": "O'Neil_%"}).text
    for key, value in [("per_page", "101"), ("page", "0"), ("q", "x"*101)]:
        assert auth.client.get("/admin/users", query_string={key: value}).status_code == 400
    assert auth.client.get("/admin/audit?end=2026-04-31").status_code == 400


def test_unknown_actions_fail_closed_for_incorrect_types(auth):
    from app.services.permission_service import academic_access, can_access_student_resource

    with auth.app.app_context():
        admin = actor(auth)
        assert can_access_student_resource(admin, auth.student_ids[0], action=[]) is False
        with pytest.raises(PermissionError):
            academic_access(admin, {})


def test_oversized_form_is_rejected_without_showing_body(client):
    response = client.post("/login", data={"username": "x" * (1024 * 1024), "password": "local-fixture-marker"})
    assert response.status_code == 413
    assert "local-fixture-marker" not in response.text
