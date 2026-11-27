"""Student status, archival flag and current class are independent."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"
    __table_args__ = (CheckConstraint("status IN ('enrolled','suspended','graduated','withdrawn')", name="ck_students_status"),)

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))
    class_id: Mapped[int | None] = mapped_column(ForeignKey("school_classes.class_id", ondelete="RESTRICT"), index=True)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enrolled", server_default="enrolled", index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="ck_students_is_archived"), nullable=False, default=False, server_default=text("0"))

    school_class: Mapped["SchoolClass | None"] = relationship(back_populates="students")
    user: Mapped["User | None"] = relationship(back_populates="student", passive_deletes="all", uselist=False)
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student", passive_deletes="all")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="student", passive_deletes="all")
    reward_records: Mapped[list["RewardRecord"]] = relationship(back_populates="student", passive_deletes="all")
    parents: Mapped[list["Parent"]] = relationship(back_populates="student", passive_deletes="all")
    contact_logs: Mapped[list["ParentContactLog"]] = relationship(back_populates="student", passive_deletes="all")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="student", passive_deletes="all")
