import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import NotificationLog, Parent
from archive_support import submit
from student_records_support import CONTACT, actor, scoped_teacher, student_records


def test_contact_preserves_linked_snapshot_and_does_not_create_notice(student_records):
    from app.services.parent_contact_service import create_contact, get_contact, update_contact

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth)
        row = create_contact(operator, ids.own, {**CONTACT, "parent_id": ids.parent})
        db.session.commit()
        assert row.contact_person_name == "本班虚构家长" and row.contact_person_phone == "000-4011"
        db.session.get(Parent, ids.parent).phone = "000-4099"
        db.session.commit()
        update_contact(operator, row.contact_id, {**CONTACT, "content": "更新内容"})
        saved = get_contact(operator, row.contact_id)
        assert saved.content == "更新内容" and saved.contact_person_phone == "000-4011"
        assert db.session.scalar(select(NotificationLog)) is None


@pytest.mark.parametrize("change", [{"parent_id": "outside"}, {"parent_id": 9999}, {"contact_person_name": " "},
                                    {"contact_person_name": None}, {"contact_person_name": "临时", "method": "bad"}])
def test_contact_rejects_invalid_parent_and_missing_explicit_name(student_records, change):
    from app.services.parent_contact_service import create_contact

    auth, ids = student_records.auth, student_records.ids
    if change.get("parent_id") == "outside":
        change = {"parent_id": ids.other_parent}
    with auth.app.app_context(), pytest.raises(ValueError):
        create_contact(actor(auth), ids.own, {**CONTACT, **change})


def test_contact_browser_forms_and_filters(student_records):
    auth, ids = student_records.auth, student_records.ids
    data = {**CONTACT, "contacted_at": "2026-11-19T08:30"}
    created = submit(auth, "/records/contacts/new", {**data, "student_id": ids.own, "parent_id": ids.parent})
    assert created.status_code == 303 and "私人沟通正文" in auth.client.get(created.location).text
    edited = submit(auth, created.location + "/edit", {**data, "result": "已更新联系结果"})
    assert edited.status_code == 303 and "已更新联系结果" in auth.client.get(edited.location).text
    page = auth.client.get(f"/records/contacts?student_id={ids.own}&parent_id={ids.parent}&start=2026-11-19&end=2026-11-19")
    assert page.status_code == 200 and "本班虚构家长" in page.text and "外班联系人" not in page.text
