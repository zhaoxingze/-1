"""The three supported role codes; IDs are deliberately not fixed."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"
    __table_args__ = (CheckConstraint("name IN ('admin','teacher','student')", name="ck_roles_name"),)

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(200))

    users: Mapped[list["User"]] = relationship(back_populates="role", passive_deletes="all")
