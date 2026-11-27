"""Courses retain only their current teacher relationship."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Course(db.Model):
    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    course_name: Mapped[str] = mapped_column(String(100), nullable=False)
    credit: Mapped[float] = mapped_column(Float, nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.teacher_id", ondelete="RESTRICT"), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    teacher: Mapped["Teacher | None"] = relationship(back_populates="courses")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course", passive_deletes="all")
