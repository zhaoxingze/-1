"""CSRF checks use test-only routes, never production debug endpoints."""

from flask_wtf.csrf import generate_csrf


def test_post_without_csrf_token_is_rejected(app):
    app.add_url_rule("/_test/write", view_func=lambda: "accepted", methods=["POST"])
    assert app.test_client().post("/_test/write").status_code == 400


def test_post_with_valid_csrf_token_is_accepted(app):
    app.add_url_rule("/_test/token", endpoint="test_token", view_func=lambda: {"token": generate_csrf()})
    app.add_url_rule("/_test/write", endpoint="test_write", view_func=lambda: "accepted", methods=["POST"])
    client = app.test_client()
    token = client.get("/_test/token").json["token"]
    response = client.post("/_test/write", data={"csrf_token": token})
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "accepted"
