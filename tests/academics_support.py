from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Enrollment, Student, User
from teacher_scope_support import scoped_teacher

TERM = "2026-Fall"
PAST = "2026-Spring"
COURSE_DATA = {"course_code": "AC-C03", "course_name": "虚构新课程", "credit": "2.5", "teacher_id": "0"}


@pytest.fixture
def academic(scoped_teacher):
    auth, ids = scoped_teacher
    with auth.app.app_context():
        rows = [
            Enrollment(student_id=ids.course_only, course_id=ids.own_course, semester=TERM),
            Enrollment(student_id=ids.own, course_id=ids.own_course, semester=PAST,
                       usual_score=80, exam_score=90, total_score=87),
            Enrollment(student_id=ids.unrelated, course_id=ids.other_course, semester=TERM),
        ]
        db.session.add_all(rows)
        db.session.commit()
        current, past, other = [row.enrollment_id for row in rows]
    return SimpleNamespace(auth=auth, ids=ids, current=current, past=past, other=other)


def actor(academic, name="auth_teacher"):
    return db.session.get(User, academic.auth.ids[name])


def sign_in(academic, name):
    auth = academic.auth
    auth.client.post("/logout", data={"csrf_token": auth.token("/profile")})
    assert auth.login(name).status_code == 303
