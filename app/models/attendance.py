"""Student/date/period attendance records, independently of courses."""

from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date", "period", name="uq_attendance_student_date_period"),
        CheckConstraint("status IN ('present','late','absent','leave')", name="ck_attendance_status"),
    )

    attendance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)

    student: Mapped["Student"] = relationship(back_populates="attendance_records")
    recorder: Mapped["User"] = relationship(back_populates="attendance_records")
