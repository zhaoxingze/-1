from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import AttendanceRecord, Course, Enrollment, Parent, ParentContactLog, Teacher, User
from teacher_scope_support import scoped_teacher


DAY = date(2026, 11, 19)
ATTENDANCE = {"attendance_date": DAY, "period": "课间集合", "status": "present", "note": "内部备注样例"}
REWARD = {"record_type": "reward", "category": "优秀志愿者", "description": "私人事由样例", "occurred_on": DAY}
CONTACT = {"method": "phone", "content": "私人沟通正文", "result": "私人联系结果",
           "contacted_at": datetime(2026, 11, 19, 8, 30)}
NOTICE = {"channel": "sms", "content": "私人模拟通知正文"}


@pytest.fixture
def student_records(scoped_teacher, auth_password_hash):
    auth, ids = scoped_teacher
    with auth.app.app_context():
        teacher = Teacher(name="仅任课示例教师", teacher_no="RECORD-T3")
        user = User(username="only_course", role=actor(auth).role, teacher=teacher,
                    password_hash=auth_password_hash)
        course = Course(course_code="RECORD-C3", course_name="任课示例", credit=1, teacher=teacher)
        outside = AttendanceRecord(student_id=ids.course_only, attendance_date=DAY, period="课间集合",
                                   status="absent", recorded_by=auth.ids["auth_admin"])
        contact = ParentContactLog(student_id=ids.course_only, method="phone", content="外班私密内容",
                                   contact_person_name="外班联系人", created_by=auth.ids["auth_admin"])
        db.session.add_all([user, Enrollment(student_id=ids.own, course=course, semester="2026-Fall"),
                            outside, contact])
        db.session.commit()
        ids.parent = db.session.scalar(select(Parent.parent_id).where(Parent.student_id == ids.own))
        ids.other_parent = db.session.scalar(select(Parent.parent_id).where(Parent.student_id == ids.course_only))
        ids.other_attendance = outside.attendance_id
        ids.other_contact = contact.contact_id
        auth.ids[user.username] = user.user_id
    return SimpleNamespace(auth=auth, ids=ids)


def actor(auth, username="auth_teacher"):
    return db.session.get(User, auth.ids[username])


def sign_in(auth, username):
    auth.client.post("/logout", data={"csrf_token": auth.token("/profile")})
    assert auth.login(username).status_code == 303
