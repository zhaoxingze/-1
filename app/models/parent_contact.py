"""Parent-contact history includes explicit contacts when no parent is linked."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from .types import UTCNaiveDateTime, utc_now


class ParentContactLog(db.Model):
    __tablename__ = "parent_contact_logs"
    __table_args__ = (
        CheckConstraint("method IN ('phone','in_person','sms','email','other')", name="ck_parent_contacts_method"),
        CheckConstraint("parent_id IS NOT NULL OR (contact_person_name IS NOT NULL AND length(trim(contact_person_name, char(9)||char(10)||char(11)||char(12)||char(13)||' ')) > 0)", name="ck_parent_contacts_explicit_name"),
    )

    contact_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("parents.parent_id", ondelete="RESTRICT"), index=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(Text)
    contacted_at: Mapped[datetime] = mapped_column(UTCNaiveDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp(), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    contact_person_name: Mapped[str | None] = mapped_column(String(50))
    contact_person_phone: Mapped[str | None] = mapped_column(String(30))

    student: Mapped["Student"] = relationship(back_populates="contact_logs")
    parent: Mapped["Parent | None"] = relationship(back_populates="contact_logs")
    creator: Mapped["User"] = relationship(back_populates="contact_logs")
