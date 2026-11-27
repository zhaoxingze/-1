from flask import abort, current_app, render_template, request, url_for

from app.admin.archive_views import list_params, load, read_id, strict_form
from app.services.archive_common import ArchiveValidationError
from app.services.enrollment_service import course_options, list_enrollments, semester_options, semester_value
from app.services.permission_service import GRADE_READ
from . import bp


def read_term(*, allow_all=True):
    raw = request.args.get("semester", current_app.config["ACTIVE_SEMESTER"])
    if raw == "" and allow_all:
        return None
    try:
        return semester_value(raw)
    except ArchiveValidationError:
        abort(400)


def render_records(action):
    term = read_term()
    course_id = read_id("course_id")
    student_id = read_id("student_id")
    params = list_params()
    records = load(list_enrollments, action=action, semester=term, course_id=course_id,
                   student_id=student_id, **params)
    return render_template("academics/records.html", records=records, grades=action == GRADE_READ,
                           term=term, course_id=course_id, student_id=student_id, q=params["q"],
                           terms=load(semester_options, action, course_id=course_id),
                           courses=load(course_options, action))


@bp.context_processor
def academic_template_helpers():
    def page_url(page, page_name="page"):
        allowed = {"q", "per_page", "semester", "course_id", "student_id"}
        values = {key: value for key, value in request.args.items() if key in allowed}
        return url_for(request.endpoint, **values, **{page_name: page})

    return {"page_url": page_url}
