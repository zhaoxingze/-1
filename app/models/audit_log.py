"""Append-only operation records, with credential-free JSON snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.extensions import db
from .security import sanitize_snapshot
from .types import UTCNaiveDateTime, utc_now


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (CheckConstraint("action IN ('create','update','archive','restore','status_change','delete')", name="ck_audit_logs_action"),)

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(UTCNaiveDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp(), index=True)
    request_id: Mapped[str | None] = mapped_column(String(100))

    actor: Mapped["User | None"] = relationship(back_populates="audit_logs")

    @validates("before_data", "after_data")
    def _sanitize_snapshot(self, key, value):
        return sanitize_snapshot(value)
