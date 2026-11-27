from flask import render_template, url_for
from flask_login import current_user

from app.admin.archive_views import editor, list_params, load, payload, references, set_choices
from app.services.course_service import COURSE_FIELDS, count_course_enrollments, create_course, get_course, list_courses, update_course
from app.services.enrollment_service import semester_options
from app.services.permission_service import role_required
from . import bp
from .forms import CourseForm
from .views import read_term, strict_form


@bp.get("/courses")
@role_required("admin", "teacher", "student")
def courses():
    params = list_params()
    return render_template("academics/courses.html", courses=load(list_courses, **params), q=params["q"])


@bp.get("/courses/<int:course_id>")
@role_required("admin", "teacher", "student")
def course_detail(course_id):
    row = load(get_course, course_id)
    term = read_term(allow_all=False)
    return render_template("academics/course_detail.html", course=row, term=term,
                           terms=load(semester_options, course_id=course_id),
                           count=load(count_course_enrollments, course_id, term))


def course_editor(row=None):
    strict_form(*COURSE_FIELDS)
    form = CourseForm(obj=row)
    set_choices(form, "teacher_id", references("teachers")["teachers"])

    def operation():
        data = payload(form, COURSE_FIELDS)
        data["teacher_id"] = data["teacher_id"] or None
        if row is None:
            return create_course(current_user, data)
        return update_course(current_user, row.course_id, data)

    return editor(form, title="新增课程" if row is None else "编辑课程", operation=operation,
                  success_url=lambda saved: url_for("academics.course_detail", course_id=saved.course_id),
                  back_url=url_for("academics.courses") if row is None else
                  url_for("academics.course_detail", course_id=row.course_id))


@bp.route("/courses/new", methods=["GET", "POST"])
@role_required("admin")
def course_new():
    return course_editor()


@bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def course_edit(course_id):
    return course_editor(load(get_course, course_id))
