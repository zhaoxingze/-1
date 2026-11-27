"""Public pages and role-specific workbenches."""

from flask import jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.services.dashboard_statistics_service import student_statistics, teacher_statistics
from app.services.permission_service import role_required

from . import bp
from .navigation import WORKBENCH
from .views import dashboard_page_url, dashboard_view


@bp.get("/")
def index():
    return render_template("dashboard/index.html")


@bp.get("/health")
def health():
    """Application liveness only; this does not claim database readiness."""
    return jsonify(status="ok", service="student-management-system")


@bp.get("/dashboard")
@role_required("admin", "teacher", "student")
def workbench():
    return redirect(url_for(WORKBENCH[current_user.role.name]))


@bp.get("/dashboard/teacher")
@role_required("teacher")
def teacher():
    stats = dashboard_view(teacher_statistics)
    return render_template("dashboard/workbench.html", role_label="教师", stats=stats, page_url=dashboard_page_url)


@bp.get("/dashboard/student")
@role_required("student")
def student():
    return render_template("dashboard/workbench.html", role_label="学生",
                           stats=dashboard_view(student_statistics, filters=False))


@bp.get("/profile")
@login_required
def profile():
    return render_template("dashboard/profile.html")
