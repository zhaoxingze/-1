from flask import abort, request, url_for

from app.admin.archive_views import load, read_id, read_int
from app.services.attendance_service import STATUSES


def dashboard_view(service, *, filters=True):
    allowed = {"semester", "class_id", "course_page"} if filters else set()
    if request.args.keys() - allowed:
        abort(403)
    if any(len(values) != 1 for _, values in request.args.lists()):
        abort(400)
    args = {"semester": request.args.get("semester"), "class_id": read_id("class_id"),
            "course_page": read_int("course_page", 1)} if filters else {}
    stats = load(service, **args)
    stats["attendance_labels"] = STATUSES
    return stats


def dashboard_page_url(number, page_name):
    args = {key: request.args[key] for key in ("semester", "class_id") if key in request.args}
    return url_for(request.endpoint, **args, **{page_name: number})
