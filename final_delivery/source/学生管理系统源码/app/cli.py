"""Explicit, transactional database setup; never runs at application import."""

from datetime import date, datetime

import click
from flask import Flask
from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from .extensions import db


def _snapshot(entity):
    result = {}
    for column in inspect(type(entity)).columns:
        value = getattr(entity, column.key)
        result[column.key] = value.isoformat() if isinstance(value, (date, datetime)) else value
    return result


def _new(model, lookup, values, *, actor_user_id=None):
    """Seed only missing named demonstration records; do not overwrite data."""
    from .services.audit_service import record_create

    existing = db.session.scalar(select(model).filter_by(**lookup))
    if existing is not None:
        return existing, False
    entity = model(**(values | lookup))
    db.session.add(entity)
    db.session.flush()
    primary_key = inspect(model).primary_key[0].key
    record_create(model.__name__, getattr(entity, primary_key), actor_user_id=actor_user_id,
                  after_data=_snapshot(entity))
    return entity, True


def register_cli(app: Flask) -> None:
    @app.cli.command("seed-roles")
    def seed_roles():
        """Idempotently create role names, without relying on numeric IDs."""
        from .models import Role

        try:
            added = sum(_new(Role, {"name": name}, {"description": description})[1]
                        for name, description in (("admin", "管理员"), ("teacher", "教师"), ("student", "学生")))
            db.session.commit()
        except (SQLAlchemyError, ValueError) as error:
            db.session.rollback()
            raise click.ClickException("角色初始化失败，事务已回滚；请确认迁移已完成。") from error
        click.echo(f"Roles ready; added {added}.")

    @app.cli.command("create-admin")
    def create_admin():
        """Interactively create an administrator; there is no default password."""
        from .models import Role, User
        from .services.audit_service import record_create
        from .services.data_validation_service import validate_user_profile_binding

        username = click.prompt("管理员用户名").strip()
        if not username or len(username) > 50 or "\x00" in username:
            raise click.ClickException("用户名须为 1 到 50 个有效字符。")
        if db.session.scalar(select(User).where(User.username == username)) is not None:
            raise click.ClickException("用户名已存在，拒绝重复创建。")
        role = db.session.scalar(select(Role).where(Role.name == "admin"))
        if role is None:
            raise click.ClickException("请先运行 flask seed-roles。")
        password = click.prompt("管理员密码", hide_input=True, confirmation_prompt="再次输入管理员密码")
        if not 1 <= len(password) <= 1024:
            raise click.ClickException("密码须为 1 到 1024 个字符。")
        try:
            user = User(username=username, password_hash=generate_password_hash(password), role=role,
                        is_active=True)
            validate_user_profile_binding(user)
            db.session.add(user)
            db.session.flush()
            record_create("User", user.user_id, after_data={"username": username, "role": "admin"})
            db.session.commit()
        except (SQLAlchemyError, ValueError) as error:
            db.session.rollback()
            raise click.ClickException("管理员创建失败，事务已回滚。") from error
        click.echo("Administrator created; no plaintext password stored.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Create fictional records without creating any demonstration accounts."""
        from .models import (AttendanceRecord, Course, Enrollment, NotificationLog, Parent,
                             ParentContactLog, RewardRecord, Role, SchoolClass, Student, Teacher, User)
        from .services.audit_service import record_create
        from .services.notification_service import create_simulated_notification

        actor = db.session.scalar(select(User).join(Role).where(
            Role.name == "admin", User.is_active.is_(True), User.student_id.is_(None), User.teacher_id.is_(None)
        ).order_by(User.user_id))
        if actor is None:
            raise click.ClickException("必须先创建管理员账号；演示数据不创建默认账号。")
        added = 0
        def ensure(model, lookup, values):
            nonlocal added
            entity, was_added = _new(model, lookup, values, actor_user_id=actor.user_id)
            added += int(was_added)
            return entity

        try:
            teacher = ensure(Teacher, {"teacher_no": "DEMO-T001"},
                             {"name": "虚构教师甲", "phone": "000-0000-0001", "email": "teacher@example.invalid"})
            school_class = ensure(SchoolClass, {"class_name": "DEMO 演示班", "grade": "演示年级", "homeroom_teacher_id": teacher.teacher_id}, {})
            student = ensure(Student, {"student_no": "DEMO-S001"},
                             {"name": "虚构学生甲", "gender": "未指定", "birth_date": date(2008, 1, 1),
                              "class_id": school_class.class_id, "enrollment_date": date(2026, 9, 1), "status": "enrolled"})
            course = ensure(Course, {"course_code": "DEMO-C001"},
                            {"course_name": "DEMO 示例课程", "credit": 1.0, "teacher_id": teacher.teacher_id})
            ensure(Enrollment, {"student_id": student.student_id, "course_id": course.course_id, "semester": "2026-Fall"}, {})
            parent = ensure(Parent, {"student_id": student.student_id, "name": "虚构监护人甲", "relationship": "guardian"},
                            {"phone": "000-0000-0002", "email": "guardian@example.invalid", "is_primary": True})
            ensure(AttendanceRecord, {"student_id": student.student_id, "attendance_date": date(2026, 11, 16), "period": "DEMO-P1"},
                   {"status": "present", "recorded_by": actor.user_id})
            ensure(RewardRecord, {"student_id": student.student_id, "record_type": "reward", "description": "[DEMO] 虚构奖励记录"},
                   {"category": "演示奖励", "occurred_on": date(2026, 11, 16), "created_by": actor.user_id})
            ensure(ParentContactLog, {"student_id": student.student_id, "parent_id": parent.parent_id, "content": "[DEMO] 虚构家长联系记录"},
                   {"method": "phone", "result": "演示记录，未真实联系", "contacted_at": datetime(2026, 11, 16, 1),
                    "contact_person_name": parent.name, "contact_person_phone": parent.phone, "created_by": actor.user_id})
            notification = db.session.scalar(select(NotificationLog).where(
                NotificationLog.student_id == student.student_id, NotificationLog.content == "[DEMO] 模拟短信，无真实发送"))
            if notification is None:
                notification = create_simulated_notification(student.student_id, "sms", "[DEMO] 模拟短信，无真实发送",
                                                             created_by=actor.user_id, parent_id=parent.parent_id)
                db.session.flush()
                record_create("NotificationLog", notification.notification_id, actor_user_id=actor.user_id,
                              after_data=_snapshot(notification))
                added += 1
            db.session.commit()
        except (SQLAlchemyError, ValueError) as error:
            db.session.rollback()
            raise click.ClickException("演示初始化失败，全部新增已回滚；未覆盖既有数据。") from error
        click.echo(f"Fictional demo data ready; added {added}. No accounts or real messages created.")
