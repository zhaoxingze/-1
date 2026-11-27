"""Service validation uses actual roles/profiles and caller-owned transactions."""

from datetime import date
from decimal import Decimal

import pytest


def _student(number="S1"):
    from app.models import Student

    return Student(student_no=number, name="虚构学生", gender="unspecified", enrollment_date=date(2026, 9, 1))


@pytest.mark.parametrize("value, expected", [(0, 0.0), (100, 100.0), (87.5, 87.5), (Decimal("92.1"), 92.1), (None, None)])
def test_score_accepts_only_nullable_finite_scores(value, expected):
    from app.services.data_validation_service import validate_score_value

    assert validate_score_value(value) == expected


@pytest.mark.parametrize("value", [True, False, "90", "", float("nan"), float("inf"), -float("inf"), -0.01, 100.01, object(), complex(1, 0)])
def test_score_rejects_invalid_values(value):
    from app.services.data_validation_service import validate_score_value

    with pytest.raises(ValueError):
        validate_score_value(value)


def test_score_none_can_be_disallowed():
    from app.services.data_validation_service import validate_score_value

    with pytest.raises(ValueError):
        validate_score_value(None, allow_none=False)


def test_role_names_determine_binding_instead_of_primary_keys(test_db):
    from app.models import Role, Teacher, User
    from app.services.data_validation_service import validate_user_profile_binding

    teacher = Teacher(teacher_no="T1", name="虚构教师")
    admin_role = Role(role_id=41, name="admin")
    teacher_role = Role(role_id=72, name="teacher")
    student_role = Role(role_id=93, name="student")
    student = _student()
    test_db.session.add_all([admin_role, teacher_role, student_role, teacher, student])
    test_db.session.flush()
    for user in [User(username="admin", password_hash="hash", role_id=41), User(username="teacher", password_hash="hash", role_id=72, teacher_id=teacher.teacher_id), User(username="student", password_hash="hash", role_id=93, student_id=student.student_id)]:
        assert validate_user_profile_binding(user) is None


@pytest.mark.parametrize("role_name, student_binding, teacher_binding", [("admin", True, False), ("admin", False, True), ("teacher", False, False), ("teacher", True, True), ("student", False, False), ("student", True, True), ("student", False, True)])
def test_user_rejects_role_profile_mismatch(test_db, role_name, student_binding, teacher_binding):
    from app.models import Role, Teacher, User
    from app.services.data_validation_service import validate_user_profile_binding

    role = Role(name=role_name)
    teacher = Teacher(teacher_no="T1", name="虚构教师")
    student = _student()
    test_db.session.add_all([role, teacher, student])
    test_db.session.flush()
    user = User(username="invalid", password_hash="hash", role_id=role.role_id, student_id=student.student_id if student_binding else None, teacher_id=teacher.teacher_id if teacher_binding else None)
    with pytest.raises(ValueError):
        validate_user_profile_binding(user, session=test_db.session)


def test_user_supports_pending_relationship_graph_without_flushing(test_db):
    from app.models import Role, User
    from app.services.data_validation_service import validate_user_profile_binding

    user = User(username="pending", password_hash="hash", role=Role(name="student"), student=_student())
    test_db.session.add(user)
    validate_user_profile_binding(user)
    assert user.user_id is None
    assert user.student.student_id is None


def test_user_rejects_missing_role_and_profile(test_db):
    from app.models import Role, User
    from app.services.data_validation_service import validate_user_profile_binding

    role = Role(name="student")
    test_db.session.add(role)
    test_db.session.flush()
    for user in [User(username="x", password_hash="hash"), User(username="x", password_hash="hash", role_id=99999), User(username="x", password_hash="hash", role_id=role.role_id, student_id=99999)]:
        with pytest.raises(ValueError):
            validate_user_profile_binding(user)


def test_user_explicit_fk_change_overrides_cached_relationship(test_db):
    from app.models import Role, User
    from app.services.data_validation_service import validate_user_profile_binding

    admin, student_role = Role(name="admin"), Role(name="student")
    student = _student()
    user = User(username="change", password_hash="hash", role=student_role, student=student)
    test_db.session.add_all([admin, user])
    test_db.session.flush()
    assert user.role is student_role
    assert user.student is student
    user.role_id = admin.role_id
    user.student_id = None
    validate_user_profile_binding(user)
    user.role_id = student_role.role_id
    user.student_id = 99999
    with pytest.raises(ValueError):
        validate_user_profile_binding(user)


def test_user_rejects_profile_marked_for_deletion(test_db):
    from app.models import Role, User
    from app.services.data_validation_service import validate_user_profile_binding

    role, student = Role(name="student"), _student()
    test_db.session.add_all([role, student])
    test_db.session.flush()
    user = User(username="deleted", password_hash="hash", role=role, student=student)
    test_db.session.delete(student)
    with pytest.raises(ValueError):
        validate_user_profile_binding(user)


def test_user_relationship_assignment_takes_effect_before_fk_sync(test_db):
    from app.models import Role, User
    from app.services.data_validation_service import validate_user_profile_binding

    first, second = _student("S1"), _student("S2")
    role = Role(name="student")
    user = User(username="relationship", password_hash="hash", role=role, student=first)
    test_db.session.add_all([user, second])
    test_db.session.flush()
    user.student = second
    assert user.student_id == first.student_id
    validate_user_profile_binding(user)
    user.student = None
    with pytest.raises(ValueError):
        validate_user_profile_binding(user)


def test_parent_binding_requires_existing_matching_student(test_db):
    from app.models import Parent
    from app.services.data_validation_service import validate_parent_student_binding

    first, second = _student("S1"), _student("S2")
    parent = Parent(student=first, name="虚构家长", relationship="guardian", phone="000-100")
    test_db.session.add_all([first, second, parent])
    test_db.session.flush()
    assert validate_parent_student_binding(first.student_id, parent.parent_id) is parent
    assert validate_parent_student_binding(first.student_id, None) is None
    for student_id, parent_id in [(second.student_id, parent.parent_id), (99999, None), (first.student_id, 99999)]:
        with pytest.raises(ValueError):
            validate_parent_student_binding(student_id, parent_id, session=test_db.session)
    test_db.session.delete(parent)
    with pytest.raises(ValueError):
        validate_parent_student_binding(first.student_id, parent.parent_id)


def test_parent_binding_uses_current_unflushed_parent_student_fk(test_db):
    from app.models import Parent
    from app.services.data_validation_service import validate_parent_student_binding

    first, second = _student("S1"), _student("S2")
    parent = Parent(student=first, name="虚构家长", relationship="guardian", phone="000-100")
    test_db.session.add_all([first, second, parent])
    test_db.session.flush()
    assert parent.student is first
    parent.student_id = second.student_id
    assert validate_parent_student_binding(second.student_id, parent.parent_id) is parent
    with pytest.raises(ValueError):
        validate_parent_student_binding(first.student_id, parent.parent_id)
