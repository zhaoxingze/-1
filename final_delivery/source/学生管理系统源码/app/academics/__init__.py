"""Course, enrollment and grade module boundary."""

from flask import Blueprint

bp = Blueprint("academics", __name__, url_prefix="/academics")

from . import course_routes, enrollment_routes, grade_routes  # noqa: E402,F401
