"""Public skeleton homepage and application health routes."""

from flask import Blueprint

bp = Blueprint("dashboard", __name__)

from . import routes  # noqa: E402,F401 -- register views on this blueprint
from . import teacher_routes  # noqa: E402,F401
from . import navigation  # noqa: E402,F401
