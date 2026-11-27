"""Semester enrollments with validated individual scores, no score formula."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.extensions import db
from .types import UTCNaiveDateTime, utc_now


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "semester", name="uq_enrollments_student_course_semester"),
        CheckConstraint("usual_score IS NULL OR (usual_score >= 0 AND usual_score <= 100)", name="ck_enrollments_usual_score"),
        CheckConstraint("exam_score IS NULL OR (exam_score >= 0 AND exam_score <= 100)", name="ck_enrollments_exam_score"),
        CheckConstraint("total_score IS NULL OR (total_score >= 0 AND total_score <= 100)", name="ck_enrollments_total_score"),
    )

    enrollment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="RESTRICT"), nullable=False, index=True)
    semester: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    usual_score: Mapped[float | None] = mapped_column(Float)
    exam_score: Mapped[float | None] = mapped_column(Float)
    total_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(UTCNaiveDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")

    @validates("usual_score", "exam_score", "total_score")
    def _validate_score(self, key, value):
        from app.services.data_validation_service import validate_score_value

        return validate_score_value(value)
