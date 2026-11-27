"""Simulated notifications store an independent recipient snapshot."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from .types import UTCNaiveDateTime, utc_now


class NotificationLog(db.Model):
    __tablename__ = "notification_logs"
    __table_args__ = (
        CheckConstraint("channel IN ('sms','email')", name="ck_notification_channel"),
        CheckConstraint("status IN ('prepared','simulated','cancelled')", name="ck_notification_status"),
    )

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("parents.parent_id", ondelete="RESTRICT"), index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON(none_as_null=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="prepared", server_default="prepared")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCNaiveDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp(), index=True)

    student: Mapped["Student"] = relationship(back_populates="notification_logs")
    parent: Mapped["Parent | None"] = relationship(back_populates="notification_logs")
    creator: Mapped["User"] = relationship(back_populates="notification_logs")
