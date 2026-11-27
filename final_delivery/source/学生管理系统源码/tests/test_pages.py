"""HTTP contracts for the real skeleton routes and error handlers."""

import logging

from flask import abort


def test_homepage_is_accessible_without_authentication(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "学生综合信息管理系统" in response.get_data(as_text=True)
    assert 'href="/health"' in response.get_data(as_text=True)


def test_health_reports_application_liveness(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.json == {"status": "ok", "service": "student-management-system"}


def test_missing_page_returns_custom_404(client):
    response = client.get("/a-page-that-does-not-exist")
    assert response.status_code == 404
    assert "页面未找到" in response.get_data(as_text=True)
    assert 'href="/"' in response.get_data(as_text=True)


def test_forbidden_request_returns_custom_403(app):
    def forbidden():
        abort(403)

    app.add_url_rule("/_test/forbidden", view_func=forbidden)
    response = app.test_client().get("/_test/forbidden")
    assert response.status_code == 403
    assert "访问受限" in response.get_data(as_text=True)


def test_unexpected_error_returns_generic_500_and_logs_exception(app, caplog):
    def broken():
        raise RuntimeError("sensitive-internal-detail")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.add_url_rule("/_test/broken", view_func=broken)
    with caplog.at_level(logging.ERROR, logger=app.logger.name):
        response = app.test_client().get("/_test/broken")
    assert response.status_code == 500
    assert "服务暂时不可用" in response.get_data(as_text=True)
    assert "sensitive-internal-detail" not in response.get_data(as_text=True)
    assert any(record.exc_info for record in caplog.records)


def test_local_stylesheets_are_served(client):
    for path in ("/static/css/app.css", "/static/vendor/bootstrap-5.3.3.min.css"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.mimetype == "text/css"
        assert len(response.data) > 100
