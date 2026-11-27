"""Per-student parent contacts, with at most one primary contact."""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.extensions import db


class Parent(db.Model):
    __tablename__ = "parents"
    __table_args__ = (
        CheckConstraint("relationship IN ('father','mother','guardian','other')", name="ck_parents_relationship"),
        Index("uq_parents_primary_per_student", "student_id", unique=True, sqlite_where=text("is_primary = 1")),
    )

    parent_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    relationship: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="ck_parents_is_primary"), nullable=False, default=False, server_default=text("0"))

    student: Mapped["Student"] = orm_relationship(back_populates="parents")
    contact_logs: Mapped[list["ParentContactLog"]] = orm_relationship(back_populates="parent", passive_deletes="all")
    notification_logs: Mapped[list["NotificationLog"]] = orm_relationship(back_populates="parent", passive_deletes="all")
