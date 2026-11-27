import json

import pytest
from sqlalchemy import select, text

from app.extensions import db
from app.models import AttendanceRecord, AuditLog, NotificationLog, ParentContactLog, RewardRecord
from archive_support import submit
from student_records_support import ATTENDANCE, CONTACT, NOTICE, REWARD, actor, scoped_teacher, student_records


def test_audited_records_include_actor_and_metadata_without_private_text(student_records):
    from app.services.attendance_service import create_attendance, update_attendance
    from app.services.parent_contact_service import create_contact, simulate_notification, update_contact
    from app.services.reward_service import create_reward, update_reward

    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        operator = actor(auth)
        attendance = create_attendance(operator, ids.own, ATTENDANCE)
        update_attendance(operator, attendance.attendance_id, {**ATTENDANCE, "status": "late"})
        reward = create_reward(operator, ids.own, REWARD)
        create_reward(operator, ids.own, {**REWARD, "record_type": "punishment"})
        update_reward(operator, reward.record_id, {**REWARD, "category": "优秀服务"})
        contact = create_contact(operator, ids.own, {**CONTACT, "parent_id": ids.parent})
        update_contact(operator, contact.contact_id, {**CONTACT, "result": "新的私密结果"})
        simulate_notification(operator, ids.own, {**NOTICE, "parent_id": ids.parent})
        db.session.commit()
        logs = db.session.scalars(select(AuditLog).order_by(AuditLog.audit_id)).all()
        assert len(logs) == 8 and all(row.actor_user_id == operator.user_id and row.created_at for row in logs)
        assert logs[1].before_data["status"] == "present" and logs[1].after_data["status"] == "late"
        assert logs[6].before_data["method"] == "phone" and logs[6].after_data["changed_fields"] == ["result"]
        raw = json.dumps([row.after_data for row in logs], ensure_ascii=False)
        for value in ("私人沟通正文", "私人事由样例", "内部备注样例", "本班虚构家长", "000-4011",
                      "own@example.invalid", "私人模拟通知正文", "新的私密结果"):
            assert value not in raw


@pytest.mark.parametrize("module", ["attendance", "reward", "contact", "notification"])
def test_real_audit_failure_rolls_back_writes(student_records, module):
    auth, ids = student_records.auth, student_records.ids
    with auth.app.app_context():
        db.session.execute(text("CREATE TRIGGER stage6_reject_audit BEFORE INSERT ON audit_logs "
                                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"))
        db.session.commit()
    choices = {
        "attendance": ("/attendance/new", ATTENDANCE, AttendanceRecord),
        "reward": ("/records/rewards/new", REWARD, RewardRecord),
        "contact": ("/records/contacts/new", {**CONTACT, "contacted_at": "2026-11-19T08:30", "parent_id": ids.parent}, ParentContactLog),
        "notification": ("/records/notifications/new", {**NOTICE, "parent_id": ids.parent}, NotificationLog),
    }
    path, data, model = choices[module]
    assert submit(auth, path, {**data, "student_id": ids.own}).status_code == 409
    with auth.app.app_context():
        assert db.session.scalar(select(model).where(model.student_id == ids.own)) is None
        assert db.session.scalar(select(AuditLog)) is None


def test_audit_failure_on_edit_preserves_prior_state(student_records):
    auth, ids = student_records.auth, student_records.ids
    created = submit(auth, "/attendance/new", {**ATTENDANCE, "student_id": ids.own})
    assert created.status_code == 303
    with auth.app.app_context():
        db.session.execute(text("CREATE TRIGGER stage6_reject_edit BEFORE INSERT ON audit_logs "
                                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"))
        db.session.commit()
    assert submit(auth, created.location + "/edit", {**ATTENDANCE, "status": "absent"}).status_code == 409
    with auth.app.app_context():
        row = db.session.get(AttendanceRecord, int(created.location.split("/")[-1]))
        assert row.status == "present"
        assert len(db.session.scalars(select(AuditLog)).all()) == 1
