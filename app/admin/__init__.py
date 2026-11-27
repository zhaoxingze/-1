"""Administrator archives, accounts and audit history."""

from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import routes  # noqa: E402,F401
from . import class_routes, parent_routes, student_routes, teacher_routes  # noqa: E402,F401
from . import audit_routes, user_routes  # noqa: E402,F401
