import pytest

from app.extensions import db
from archive_support import submit
from student_records_support import REWARD, actor, scoped_teacher, student_records


@pytest.mark.parametrize("record_type", ["reward", "punishment"])
def test_homeroom_teacher_creates_reward_record(student_records, record_type):
    from app.services.reward_service import create_reward, list_rewards, update_reward

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth)
        row = create_reward(operator, ids.own, {**REWARD, "record_type": record_type})
        assert row.created_by == operator.user_id
        update_reward(actor(auth, "auth_admin"), row.record_id, {**REWARD, "record_type": record_type,
                                                               "category": "编辑后类别"})
        assert row.created_by == operator.user_id
        assert list_rewards(operator, record_type=record_type, student_id=ids.own).total == 1


@pytest.mark.parametrize("change", [{"record_type": "unknown"}, {"category": " "}, {"category": "超" * 51},
                                    {"description": ""}, {"description": "a\x00b"}])
def test_reward_validates_type_and_text(student_records, change):
    from app.services.reward_service import create_reward

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context(), pytest.raises(ValueError):
        create_reward(actor(auth), ids.own, {**REWARD, **change})


def test_reward_create_detail_edit_and_list(student_records):
    auth, ids = student_records.auth, student_records.ids
    created = submit(auth, "/records/rewards/new", {**REWARD, "student_id": ids.own})
    assert created.status_code == 303 and "优秀志愿者" in auth.client.get(created.location).text
    edited = submit(auth, created.location + "/edit", {**REWARD, "category": "服务表彰"})
    assert edited.status_code == 303
    listed = auth.client.get(f"/records/rewards?student_id={ids.own}&record_type=reward&category=服务表彰&start=2026-11-19")
    assert listed.status_code == 200 and "服务表彰" in listed.text and "优秀志愿者" not in listed.text
