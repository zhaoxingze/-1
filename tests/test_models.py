"""Frozen model contract and observable ORM relationship behaviour."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select

from app.extensions import db


MODEL_NAMES = {
    "Role", "Teacher", "SchoolClass", "Student", "User", "Course",
    "Enrollment", "AttendanceRecord", "RewardRecord", "Parent",
    "ParentContactLog", "AuditLog", "NotificationLog",
}


def test_all_domain_models_are_exported():
    import app.models as models

    assert MODEL_NAMES <= set(vars(models))


def test_frozen_fields_and_restrict_foreign_keys(test_db):
    expected = {
        "roles": "role_id name description",
        "teachers": "teacher_id teacher_no name phone email",
        "school_classes": "class_id class_name grade homeroom_teacher_id",
        "students": "student_id student_no name gender birth_date phone address class_id enrollment_date status is_archived",
        "users": "user_id username password_hash role_id student_id teacher_id is_active created_at",
        "courses": "course_id course_code course_name credit teacher_id description",
        "enrollments": "enrollment_id student_id course_id semester usual_score exam_score total_score created_at",
        "attendance_records": "attendance_id student_id attendance_date period status note recorded_by",
        "reward_records": "record_id student_id record_type category description occurred_on created_by",
        "parents": "parent_id student_id name relationship phone email is_primary",
        "parent_contact_logs": "contact_id student_id parent_id method content result contacted_at created_by contact_person_name contact_person_phone",
        "audit_logs": "audit_id actor_user_id entity_type entity_id action before_data after_data created_at request_id",
        "notification_logs": "notification_id student_id parent_id channel recipient_snapshot content status created_by created_at",
    }
    assert set(test_db.metadata.tables) == set(expected)
    assert set(inspect(test_db.engine).get_table_names()) == set(expected)
    assert sum(len(t.columns) for t in test_db.metadata.tables.values()) == 94
    assert sum(len(t.foreign_keys) for t in test_db.metadata.tables.values()) == 20
    for name, fields in expected.items():
        table = test_db.metadata.tables[name]
        assert set(table.columns.keys()) == set(fields.split())
        assert all(fk.ondelete == "RESTRICT" for fk in table.foreign_keys)
    for mapper in test_db.Model.registry.mappers:
        for relation in mapper.relationships:
            assert "delete" not in relation.cascade
            assert "delete-orphan" not in relation.cascade
            if relation.direction.name in {"ONETOMANY", "MANYTOMANY"}:
                assert relation.passive_deletes == "all"


def test_pending_object_graph_relationships_and_defaults(test_db):
    from app.models import Course, Enrollment, Parent, Role, SchoolClass, Student, Teacher, User

    teacher = Teacher(teacher_no="T1", name="Teacher")
    school_class = SchoolClass(class_name="Class 1", grade="G1", homeroom_teacher=teacher)
    student = Student(student_no="S1", name="Student", gender="unspecified", enrollment_date=date(2026, 9, 1), school_class=school_class)
    user = User(username="student", password_hash="not-a-real-hash", role=Role(name="student"), student=student)
    enrollment = Enrollment(student=student, course=Course(course_code="C1", course_name="Course", credit=1.0, teacher=teacher), semester="2026-Fall", usual_score=0, exam_score=100)
    parent = Parent(student=student, name="Parent", relationship="guardian", phone="000", is_primary=True)
    test_db.session.add_all([user, enrollment, parent])
    test_db.session.commit()
    assert student.school_class.homeroom_teacher is teacher
    assert student.enrollments == [enrollment]
    assert enrollment.course.teacher is teacher
    assert student.parents == [parent]
    assert student.user is user
    assert student.status == "enrolled"
    assert student.is_archived is False
    assert user.is_active is True
    assert enrollment.total_score is None


def test_aware_times_round_trip_as_naive_utc(test_db):
    from app.models import AuditLog, utc_now

    stamp = datetime(2026, 11, 16, 12, 34, 56, tzinfo=timezone(timedelta(hours=8)))
    log = AuditLog(entity_type="student", entity_id=1, action="create", created_at=stamp)
    test_db.session.add(log)
    test_db.session.commit()
    test_db.session.expire_all()
    stored = test_db.session.scalar(select(AuditLog))
    assert stored.created_at == datetime(2026, 11, 16, 4, 34, 56)
    assert stored.created_at.tzinfo is None
    assert utc_now().tzinfo is None


@pytest.mark.parametrize("value", [True, False, "90", "nan", float("nan"), float("inf"), float("-inf"), -0.1, 100.1])
def test_score_attributes_reject_invalid_values(value):
    from app.models import Enrollment

    for attribute in ("usual_score", "exam_score", "total_score"):
        with pytest.raises(ValueError):
            setattr(Enrollment(), attribute, value)


def test_audit_snapshot_recursively_removes_credentials(test_db):
    from app.models import AuditLog

    original = {"name": "kept", "password_hash": "secret", "nested": [{"API-KEY": "secret", "token": "secret", "safe": 1}], "profile": {"refreshToken": "secret", "phone": "000"}}
    audit = AuditLog(entity_type="student", entity_id=1, action="create", after_data=original)
    test_db.session.add(audit)
    test_db.session.commit()
    assert audit.after_data == {"name": "kept", "nested": [{"safe": 1}], "profile": {"phone": "000"}}
    assert original["password_hash"] == "secret"


def test_new_audit_nested_mutation_is_sanitized_before_flush(test_db):
    from app.models import AuditLog

    audit = AuditLog(entity_type="student", entity_id=1, action="create", after_data={"safe": {}})
    audit.after_data["safe"]["password_hash"] = "secret"
    test_db.session.add(audit)
    test_db.session.commit()
    assert audit.after_data == {"safe": {}}


@pytest.mark.parametrize("snapshot", [{"value": object()}, {"nested": [float("nan")]}, {"value": float("inf")}, {"value": -float("inf")}])
def test_direct_audit_snapshots_require_finite_json(snapshot):
    from app.models import AuditLog

    with pytest.raises(ValueError, match="JSON"):
        AuditLog(entity_type="student", entity_id=1, action="create", after_data=snapshot)
