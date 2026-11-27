"""Session authentication using the existing account model."""

from flask import Blueprint

bp = Blueprint("auth", __name__)

from . import routes  # noqa: E402,F401
