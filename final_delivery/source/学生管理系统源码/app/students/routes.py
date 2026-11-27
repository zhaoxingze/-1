from flask import abort, render_template
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Student
from app.services.permission_service import require_student_access
from . import bp


@bp.get("/<int:student_id>/profile")
@login_required
def profile(student_id):
    require_student_access(current_user, student_id)
    if student_id > 9223372036854775807:
        abort(404)
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    return render_template("dashboard/student_profile.html", student=student)
