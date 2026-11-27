import pytest

from teacher_scope_support import scoped_teacher


def test_scope_distinguishes_homeroom_from_course(scoped_teacher):
    from app.extensions import db
    from app.models import User
    from app.services.permission_service import (
        can_edit_student_contact, can_view_parent_contact, can_view_student, get_teacher_scope,
        require_teacher_student_access,
    )

    auth, ids = scoped_teacher
    with auth.app.app_context():
        teacher = db.session.get(User, auth.ids["auth_teacher"])
        scope = get_teacher_scope(teacher)
        assert scope.teacher_id == ids.teacher
        assert list(db.session.scalars(scope.class_ids)) == [ids.own_class]
        assert list(db.session.scalars(scope.course_ids)) == [ids.own_course]
        assert can_view_student(teacher, ids.own)
        assert not can_view_student(teacher, ids.course_only)
        assert can_view_student(teacher, ids.course_only, course_id=ids.own_course)
        assert not can_view_student(teacher, ids.course_only, course_id=ids.other_course)
        assert can_edit_student_contact(teacher, ids.own)
        assert not can_edit_student_contact(teacher, ids.course_only)
        assert can_view_parent_contact(teacher, ids.own)
        assert not can_view_parent_contact(teacher, ids.course_only)
        with pytest.raises(PermissionError):
            require_teacher_student_access(teacher, ids.own, action="unknown")


def test_transfers_and_reassigned_courses_change_the_next_request(scoped_teacher):
    from app.extensions import db
    from app.models import Course, Student

    auth, ids = scoped_teacher
    with auth.app.app_context():
        db.session.get(Student, ids.own).class_id = ids.other_class
        db.session.get(Course, ids.own_course).teacher_id = ids.other_teacher
        db.session.commit()
    assert auth.client.get(f"/teacher/students/{ids.own}").status_code == 403
    assert auth.client.get(f"/teacher/courses/{ids.own_course}/students").status_code == 403


def test_current_homeroom_reassignment_revokes_access(scoped_teacher):
    from app.extensions import db
    from app.models import SchoolClass

    auth, ids = scoped_teacher
    with auth.app.app_context():
        db.session.get(SchoolClass, ids.own_class).homeroom_teacher_id = ids.other_teacher
        db.session.commit()
    assert auth.client.get(f"/teacher/classes/{ids.own_class}/students").status_code == 403
    assert auth.client.get(f"/teacher/students/{ids.own}/parents").status_code == 403
