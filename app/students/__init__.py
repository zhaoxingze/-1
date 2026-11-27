"""Student, class, teacher and parent module boundary."""

from flask import Blueprint

bp = Blueprint("students", __name__, url_prefix="/students")

from . import routes  # noqa: E402,F401
