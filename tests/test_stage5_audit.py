from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.extensions import db
from app.models import AuditLog, Course, Enrollment
from academics_support import academic, scoped_teacher, COURSE_DATA, TERM, actor, sign_in
from archive_support import submit


def test_all_academic_writes_have_actor_and_grade_snapshots(academic):
    from app.services.course_service import create_course, update_course
    from app.services.enrollment_service import create_enrollment
    from app.services.grade_service import save_grades

    with academic.auth.app.app_context():
        admin = actor(academic, "auth_admin")
        data = {**COURSE_DATA, "credit": Decimal("2.5"), "teacher_id": None}
        course = create_course(admin, data)
        update_course(admin, course.course_id, {**data, "course_name": "更新测试课程"})
        enrollment = create_enrollment(admin, academic.ids.own, course.course_id, TERM)
        save_grades(admin, enrollment.enrollment_id, 80, 90)
        save_grades(admin, enrollment.enrollment_id, 100, 100)
        db.session.commit()
        logs = db.session.scalars(select(AuditLog).order_by(AuditLog.audit_id)).all()
        assert [(l.entity_type, l.action) for l in logs] == [
            ("Course", "create"), ("Course", "update"), ("Enrollment", "create"),
            ("Enrollment", "update"), ("Enrollment", "update"),
        ]
        assert all(log.actor_user_id == admin.user_id and log.created_at for log in logs)
        assert logs[-2].before_data == {"usual_score": None, "exam_score": None, "total_score": None}
        assert logs[-1].before_data == {"usual_score": 80, "exam_score": 90, "total_score": 87}
        assert logs[-1].after_data == {"usual_score": 100, "exam_score": 100, "total_score": 100}
        assert logs[-1].entity_id == enrollment.enrollment_id


@pytest.mark.parametrize("domain", ["course", "enrollment", "grade"])
def test_real_audit_insert_failure_rolls_back_academic_write(academic, domain):
    auth, ids = academic.auth, academic.ids
    sign_in(academic, "auth_admin")
    with auth.app.app_context():
        db.session.execute(text("CREATE TRIGGER reject_stage5_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'fixture failure'); END"))
        db.session.commit()
    if domain == "course":
        path, data = "/academics/courses/new", COURSE_DATA
    elif domain == "enrollment":
        path = "/academics/enrollments/new"
        data = {"course_id": ids.own_course, "student_id": ids.own, "semester": TERM}
    else:
        path, data = f"/academics/grades/{academic.current}/edit", {"usual_score": "80", "exam_score": "90"}
    response = submit(auth, path, data)
    assert response.status_code == 409 and "fixture failure" not in response.text
    with auth.app.app_context():
        assert db.session.scalar(select(Course).where(Course.course_code == "AC-C03")) is None
        assert db.session.scalar(select(Enrollment).where(Enrollment.student_id == ids.own, Enrollment.semester == TERM)) is None
        assert db.session.get(Enrollment, academic.current).total_score is None
        assert db.session.scalar(select(AuditLog)) is None
