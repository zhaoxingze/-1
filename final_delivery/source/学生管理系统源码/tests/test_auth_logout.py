def test_logout_is_post_only_and_clears_identity(auth):
    auth.login()
    assert auth.client.get("/logout").status_code == 405
    assert auth.client.get("/admin/").status_code == 200
    response = auth.client.post("/logout", data={"csrf_token": auth.token("/profile")})
    assert response.status_code == 303
    assert response.location == "/login"
    assert auth.client.get("/admin/").status_code == 302
    with auth.client.session_transaction() as session:
        assert "_user_id" not in session


def test_logout_without_login_is_safe_and_csrf_protected(auth):
    assert auth.client.post("/logout").status_code == 400
    assert auth.client.post("/logout", data={"csrf_token": auth.token()}).status_code == 303


def test_logged_in_logout_rejects_missing_or_invalid_csrf(auth):
    auth.login()
    for data in ({}, {"csrf_token": "invalid"}):
        assert auth.client.post("/logout", data=data).status_code == 400
        assert auth.client.get("/profile").status_code == 200
