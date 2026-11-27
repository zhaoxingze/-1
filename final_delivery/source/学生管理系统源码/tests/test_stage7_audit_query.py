from datetime import datetime

import pytest

from app.extensions import db
from app.models import AuditLog


@pytest.fixture
def historical_audit(auth):
    with auth.app.app_context():
        rows = [
            dict(actor_user_id=auth.ids["auth_admin"], entity_type="User", entity_id=4, action="update",
                 before_data={"role": "teacher"}, after_data={"role": "student", "student_id": 1, "password_hash": "unsafe-hash"},
                 created_at=datetime(2026, 11, 18, 23, 59, 59)),
            dict(actor_user_id=auth.ids["auth_admin"], entity_type="ParentContactLog", entity_id=9, action="update",
                 before_data=None, after_data={"method": "phone", "parent_id": 8, "contact_person_phone": "unsafe-phone",
                    "recipient_snapshot": {"name": "unsafe-recipient"}, "content": "unsafe-message", "token": "unsafe-token",
                    "result": "unsafe-result"}, created_at=datetime(2026, 11, 19, 23, 59, 59, 999999)),
            dict(actor_user_id=None, entity_type="ParentContactLog", entity_id=10, action="create",
                 before_data=None, after_data={"method": "email"}, created_at=datetime(2026, 11, 20)),
        ]
        db.session.execute(AuditLog.__table__.insert(), rows)
        db.session.commit()
    return auth


def test_audit_query_filters_and_paginates(historical_audit):
    auth = historical_audit
    auth.login()
    path = "/admin/audit?entity_type=ParentContactLog&per_page=1"
    page = auth.client.get(path)
    assert page.status_code == 200 and "共 2 条" in page.text and "下一页" in page.text
    assert auth.client.get(path + "&page=2").status_code == 200
    path += f"&actor_user_id={auth.ids['auth_admin']}&action=update&entity_id=9&start=2026-11-19&end=2026-11-19"
    assert "共 1 条" in auth.client.get(path).text
    assert auth.client.get("/admin/audit?start=2026-02-30").status_code == 400
    assert auth.client.get("/admin/audit?start=2026-11-21&end=2026-11-20").status_code == 400


def test_audit_detail_redacts_legacy_fields_and_is_readonly(historical_audit):
    auth = historical_audit
    auth.login()
    pages = [auth.client.get("/admin/audit/1"), auth.client.get("/admin/audit/2")]
    assert all(page.status_code == 200 for page in pages)
    assert "角色" in pages[0].text and "phone" in pages[1].text and "相关记录" in pages[1].text
    assert all("unsafe-" not in page.text for page in pages)
    assert auth.client.post("/admin/audit/2", data={"csrf_token": auth.token("/profile")}).status_code == 405
    assert auth.client.delete("/admin/audit/2", headers={"X-CSRFToken": auth.token("/profile")}).status_code == 405


@pytest.mark.parametrize("username", [None, "auth_teacher", "auth_student"])
def test_audit_denies_nonadmin(auth, username):
    if username is not None:
        auth.login(username)
    expected = 403 if username else 302
    for path in ("/admin/audit", "/admin/audit/1"):
        assert auth.client.get(path).status_code == expected
