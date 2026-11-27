"""Database commands operate only on isolated temporary test databases."""

from sqlalchemy import func, select
from werkzeug.security import check_password_hash


def test_database_commands_are_registered(app):
    assert {"seed-roles", "create-admin", "seed-demo"} <= set(app.cli.commands)


def test_seed_roles_is_idempotent(db_app):
    from app.extensions import db
    from app.models import AuditLog, Role

    runner = db_app.test_cli_runner()
    assert runner.invoke(args=["seed-roles"]).exit_code == 0
    with db_app.app_context():
        before = db.session.scalar(select(func.count()).select_from(AuditLog))
    assert runner.invoke(args=["seed-roles"]).exit_code == 0
    with db_app.app_context():
        assert set(db.session.scalars(select(Role.name))) == {"admin", "teacher", "student"}
        assert db.session.scalar(select(func.count()).select_from(AuditLog)) == before


def test_create_admin_hashes_password_and_refuses_duplicate(db_app):
    from app.extensions import db
    from app.models import AuditLog, User

    runner = db_app.test_cli_runner()
    assert runner.invoke(args=["seed-roles"]).exit_code == 0
    password = "test-only-password-93"
    result = runner.invoke(args=["create-admin"], input=f"test_admin\n{password}\n{password}\n")
    assert result.exit_code == 0, result.output
    assert password not in result.output
    with db_app.app_context():
        user = db.session.scalar(select(User).where(User.username == "test_admin"))
        assert user.role.name == "admin"
        assert user.student_id is None and user.teacher_id is None
        assert user.password_hash != password
        assert check_password_hash(user.password_hash, password)
        snapshots = str([(a.before_data, a.after_data) for a in db.session.scalars(select(AuditLog))])
        assert password not in snapshots and "password_hash" not in snapshots
    duplicate = runner.invoke(args=["create-admin"], input="test_admin\n")
    assert duplicate.exit_code != 0
    with db_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1


def test_create_admin_rejects_password_confirmation_mismatch(db_app):
    from app.extensions import db
    from app.models import User

    runner = db_app.test_cli_runner()
    runner.invoke(args=["seed-roles"])
    result = runner.invoke(args=["create-admin"], input="new_admin\nfirst\nsecond\n")
    assert result.exit_code != 0
    with db_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 0


def test_seed_demo_requires_admin_and_does_not_create_accounts(db_app):
    from app.extensions import db
    from app.models import Student, User

    runner = db_app.test_cli_runner()
    runner.invoke(args=["seed-roles"])
    result = runner.invoke(args=["seed-demo"])
    assert result.exit_code != 0
    with db_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Student)) == 0
        assert db.session.scalar(select(func.count()).select_from(User)) == 0


def test_seed_demo_is_idempotent_and_records_all_requested_domains(db_app):
    from app.extensions import db
    from app.models import (AttendanceRecord, AuditLog, Course, Enrollment, Parent,
                            ParentContactLog, RewardRecord, SchoolClass, Student, Teacher, User)

    runner = db_app.test_cli_runner()
    runner.invoke(args=["seed-roles"])
    password = "only-a-test-password"
    assert runner.invoke(args=["create-admin"], input=f"demo_operator\n{password}\n{password}\n").exit_code == 0
    first = runner.invoke(args=["seed-demo"])
    assert first.exit_code == 0, first.output
    models = (Teacher, SchoolClass, Student, Course, Enrollment, AttendanceRecord,
              Parent, RewardRecord, ParentContactLog, AuditLog, User)
    with db_app.app_context():
        before = {m.__name__: db.session.scalar(select(func.count()).select_from(m)) for m in models}
        assert all(before[m.__name__] >= 1 for m in models)
        assert before["User"] == 1
    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0, second.output
    with db_app.app_context():
        assert {m.__name__: db.session.scalar(select(func.count()).select_from(m)) for m in models} == before


def test_seed_roles_does_not_depend_on_fixed_role_ids(db_app):
    from app.extensions import db
    from app.models import Role, User

    with db_app.app_context():
        db.session.add(Role(role_id=42, name="admin", description="preexisting"))
        db.session.commit()
    runner = db_app.test_cli_runner()
    assert runner.invoke(args=["seed-roles"]).exit_code == 0
    assert runner.invoke(args=["create-admin"], input="nonfixed\nonly-test-secret\nonly-test-secret\n").exit_code == 0
    with db_app.app_context():
        assert db.session.scalar(select(User)).role_id == 42
