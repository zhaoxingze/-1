"""Accounts use role/profile validation at every ORM flush."""

from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin

from sqlalchemy import Boolean, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from .types import UTCNaiveDateTime, utc_now


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), unique=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.teacher_id", ondelete="RESTRICT"), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="ck_users_is_active"), nullable=False, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(UTCNaiveDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())

    role: Mapped["Role"] = relationship(back_populates="users")
    student: Mapped["Student | None"] = relationship(back_populates="user")
    teacher: Mapped["Teacher | None"] = relationship(back_populates="user")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="recorder", passive_deletes="all")
    reward_records: Mapped[list["RewardRecord"]] = relationship(back_populates="creator", passive_deletes="all")
    contact_logs: Mapped[list["ParentContactLog"]] = relationship(back_populates="creator", passive_deletes="all")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor", passive_deletes="all")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="creator", passive_deletes="all")

    def get_id(self) -> str:
        """Flask-Login's identity is the existing primary key, never a role ID."""
        return str(self.user_id)
