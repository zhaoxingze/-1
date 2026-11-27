"""Current school-class membership, without a transfer-history claim."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SchoolClass(db.Model):
    __tablename__ = "school_classes"

    class_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[str] = mapped_column(String(30), nullable=False)
    homeroom_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.teacher_id", ondelete="RESTRICT"), index=True)

    homeroom_teacher: Mapped["Teacher | None"] = relationship(back_populates="homeroom_classes")
    students: Mapped[list["Student"]] = relationship(back_populates="school_class", passive_deletes="all")
