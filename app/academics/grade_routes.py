from flask import url_for
from flask_login import current_user

from app.admin.archive_views import editor, load
from app.services.grade_service import get_grade_for_edit, save_grades
from app.services.permission_service import GRADE_READ, role_required
from . import bp
from .forms import GradeForm
from .views import render_records, strict_form


@bp.get("/grades")
@role_required("admin", "teacher", "student")
def grades():
    return render_records(GRADE_READ)


@bp.route("/grades/<int:enrollment_id>/edit", methods=["GET", "POST"])
@role_required("admin", "teacher")
def grade_edit(enrollment_id):
    row = load(get_grade_for_edit, enrollment_id)
    strict_form("usual_score", "exam_score")
    form = GradeForm(obj=row)
    return_to = url_for("academics.grades", course_id=row.course_id, semester=row.semester)
    return editor(
        form, title="录入成绩" if row.total_score is None else "修改成绩",
        note=f"{row.student.name} · {row.course.course_name} · {row.semester}。平时成绩占 30%，考试成绩占 70%。",
        operation=lambda: save_grades(current_user, enrollment_id, form.usual_score.data, form.exam_score.data),
        success_url=lambda saved: return_to, back_url=return_to,
    )
