"""Teacher profiles and their current teaching/class relationships."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Teacher(db.Model):
    __tablename__ = "teachers"

    teacher_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(100))

    user: Mapped["User | None"] = relationship(back_populates="teacher", passive_deletes="all", uselist=False)
    homeroom_classes: Mapped[list["SchoolClass"]] = relationship(back_populates="homeroom_teacher", passive_deletes="all")
    courses: Mapped[list["Course"]] = relationship(back_populates="teacher", passive_deletes="all")
