"""Rewards, disciplinary records and parent-contact module boundary."""

from flask import Blueprint

bp = Blueprint("records", __name__, url_prefix="/records")

from . import contact_routes, notification_routes, reward_routes  # noqa: E402,F401
