from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import AttendanceRecord, Enrollment, Student, Teacher, User
from teacher_scope_support import scoped_teacher

NEW_PASSWORD = "Disposable-fixture-password-21!"


@pytest.fixture
def unmanaged_profiles(auth):
    with auth.app.app_context():
        teachers = [Teacher(teacher_no=f"UA-T{n}", name=f"虚拟未绑定教师{n}") for n in (1, 2)]
        student = Student(student_no="UA-S1", name="虚拟未绑定学生", gender="未指定",
                          enrollment_date=date(2026, 9, 1))
        db.session.add_all([*teachers, student])
        db.session.commit()
        return SimpleNamespace(teacher=teachers[0].teacher_id, spare=teachers[1].teacher_id,
                               student=student.student_id)


def actor(auth, username="auth_admin"):
    return db.session.get(User, auth.ids[username])


def user_fields(*, username="new_account", role="admin", student_id=None, teacher_id=None):
    return {"username": username, "role": role, "student_id": student_id, "teacher_id": teacher_id}


def create_fields(**fields):
    return {**user_fields(**fields), "password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD}


TODAY = date(2026, 11, 19)
CURRENT = "2026-Fall"
PAST = "2026-Spring"


@pytest.fixture
def dashboard_data(scoped_teacher, monkeypatch):
    from app.services import dashboard_statistics_service

    auth, ids = scoped_teacher
    monkeypatch.setattr(dashboard_statistics_service, "utc_now", lambda: datetime(2026, 11, 19, 23, 45))
    with auth.app.app_context():
        db.session.get(Student, ids.course_only).is_archived = True
        db.session.get(Student, ids.unrelated).status = "graduated"
        requests = [
            (ids.own, ids.own_course, CURRENT, 84),
            (ids.course_only, ids.own_course, CURRENT, 96),
            (ids.unrelated, ids.own_course, CURRENT, None),
            (ids.unrelated, ids.other_course, CURRENT, 20),
            (ids.own, ids.own_course, PAST, 42),
        ]
        enrollments = [
            Enrollment(student_id=sid, course_id=cid, semester=term,
                       usual_score=grade, exam_score=grade, total_score=100 if grade is None else grade)
            for sid, cid, term, grade in requests
        ]
        records = [
            (ids.own, "late", TODAY), (ids.own, "leave", TODAY - timedelta(days=29)),
            (ids.course_only, "present", TODAY - timedelta(days=29)), (ids.course_only, "absent", TODAY),
            (ids.own, "absent", TODAY - timedelta(days=30)), (ids.own, "absent", TODAY + timedelta(days=1)),
        ]
        db.session.add_all([*enrollments, *(
            AttendanceRecord(student_id=sid, attendance_date=day, period=state, status=state,
                             recorded_by=auth.ids["auth_admin"])
            for sid, state, day in records
        )])
        db.session.commit()
    return auth, ids
