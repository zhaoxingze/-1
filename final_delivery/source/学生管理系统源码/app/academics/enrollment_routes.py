from flask import current_app, request, url_for
from flask_login import current_user
from wtforms.fields import SelectChoice

from app.admin.archive_views import editor, load, read_id
from app.services.enrollment_service import course_options, create_enrollment, enrollment_candidates
from app.services.permission_service import ENROLLMENT_CREATE, ENROLLMENT_READ, role_required
from . import bp
from .forms import EnrollmentForm
from .views import read_term, render_records, strict_form


@bp.get("/enrollments")
@role_required("admin", "teacher", "student")
def enrollments():
    return render_records(ENROLLMENT_READ)


@bp.route("/enrollments/new", methods=["GET", "POST"])
@role_required("admin", "teacher")
def enrollment_new():
    strict_form("course_id", "student_id", "semester")
    teacher = current_user.role.name == "teacher"
    term = current_app.config["ACTIVE_SEMESTER"] if teacher else read_term(allow_all=False)
    courses = load(course_options, ENROLLMENT_CREATE)
    students = load(enrollment_candidates)
    defaults = {"semester": term}
    if request.method == "GET":
        defaults.update(course_id=read_id("course_id") or 0, student_id=read_id("student_id") or 0)
    form = EnrollmentForm(data=defaults)
    form.course_id.choices = [SelectChoice(value=0, label="请选择课程")] + [
        SelectChoice(value=key, label=f"{code} · {name}") for key, code, name in courses
    ]
    form.student_id.choices = [SelectChoice(value=0, label="请选择学生")] + [
        SelectChoice(value=key, label=f"{number} · {name}") for key, number, name in students
    ]
    if teacher:
        form.semester.render_kw = {"readonly": True}

    return editor(
        form, title="新增选课",
        note="可为本班学生添加当前学期的本人授课课程。" if teacher else "按学生、课程和学期新增选课。",
        operation=lambda: create_enrollment(current_user, form.student_id.data, form.course_id.data,
                                            form.semester.data),
        success_url=lambda row: url_for("academics.enrollments", course_id=row.course_id, semester=row.semester),
        back_url=url_for("academics.enrollments", semester=term),
    )
