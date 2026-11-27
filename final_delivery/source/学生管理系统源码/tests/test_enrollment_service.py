import pytest

from app.extensions import db
from academics_support import academic, scoped_teacher, PAST, TERM, actor


@pytest.mark.parametrize("username", ["auth_admin", "auth_teacher"])
def test_create_ungraded_enrollment_for_student_without_current_enrollment(academic, username):
    from app.services.enrollment_service import create_enrollment

    with academic.auth.app.app_context():
        ids = academic.ids
        row = create_enrollment(actor(academic, username), ids.own, ids.own_course, TERM)
        db.session.commit()
        assert (row.usual_score, row.exam_score, row.total_score) == (None, None, None)
        with pytest.raises(ValueError, match="已选"):
            create_enrollment(actor(academic, username), ids.own, ids.own_course, TERM)
        db.session.rollback()


@pytest.mark.parametrize("student,course,term", [
    ("course_only", "own_course", TERM),
    ("own", "other_course", TERM),
    ("own", "own_course", PAST),
])
def test_teacher_must_meet_all_a22_constraints(academic, student, course, term):
    from app.services.enrollment_service import create_enrollment

    with academic.auth.app.app_context():
        ids = academic.ids
        with pytest.raises(PermissionError):
            create_enrollment(actor(academic), getattr(ids, student), getattr(ids, course), term)
        db.session.rollback()


@pytest.mark.parametrize("student,course", [(999999, 1), (1, 999999)])
def test_admin_cannot_create_record_with_missing_fk(academic, student, course):
    from app.services.enrollment_service import create_enrollment

    with academic.auth.app.app_context():
        with pytest.raises(LookupError):
            create_enrollment(actor(academic, "auth_admin"), student, course, TERM)
        db.session.rollback()


def test_configured_semester_controls_teacher_write(academic):
    from app.services.enrollment_service import create_enrollment

    academic.auth.app.config["ACTIVE_SEMESTER"] = "COURSE-DEMO-TERM"
    with academic.auth.app.app_context():
        with pytest.raises(PermissionError):
            create_enrollment(actor(academic), academic.ids.own, academic.ids.own_course, TERM)
        db.session.rollback()
        row = create_enrollment(actor(academic), academic.ids.own, academic.ids.own_course, "COURSE-DEMO-TERM")
        assert row.semester == "COURSE-DEMO-TERM"
        db.session.rollback()
