"""Rewards and punishments retain the original shared record schema."""

from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class RewardRecord(db.Model):
    __tablename__ = "reward_records"
    __table_args__ = (CheckConstraint("record_type IN ('reward','punishment')", name="ck_reward_record_type"),)

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)

    student: Mapped["Student"] = relationship(back_populates="reward_records")
    creator: Mapped["User"] = relationship(back_populates="reward_records")
