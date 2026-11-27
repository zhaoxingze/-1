from flask import abort, current_app, redirect, render_template, session, url_for
from flask_login import current_user, logout_user
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from app.auth.forms import LookupUserForm, ResetPasswordForm
from app.extensions import db
from app.models import User
from app.dashboard.views import dashboard_page_url, dashboard_view
from app.services.dashboard_statistics_service import admin_statistics
from app.services.permission_service import role_required
from . import bp


@bp.get("/")
@role_required("admin")
def index():
    stats = dashboard_view(admin_statistics)
    return render_template("dashboard/workbench.html", role_label="管理员", stats=stats,
                           page_url=dashboard_page_url)


@bp.route("/password-reset", methods=["GET", "POST"])
@role_required("admin")
def password_reset_lookup():
    form = LookupUserForm()
    error = None
    if form.validate_on_submit():
        target = db.session.scalar(select(User).where(User.username == form.username.data))
        if target is not None:
            return redirect(url_for("admin.reset_password", user_id=target.user_id), code=303)
        error = "未找到该账号，请核对用户名。"
    return render_template("auth/password_lookup.html", form=form, error=error)


@bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@role_required("admin")
def reset_password(user_id):
    from app.services.password_service import reset_user_password

    if user_id > 9223372036854775807:
        abort(404)
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)
    form = ResetPasswordForm()
    error = None
    if form.validate_on_submit():
        try:
            reset_user_password(current_user, user_id, form.admin_password.data, form.new_password.data)
            db.session.commit()
        except (ValueError, PermissionError, LookupError):
            db.session.rollback()
            error = "管理员密码验证失败或目标账号无效。"
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.error("security.password_reset_storage_failure")
            error = "密码重置失败，请稍后重试。"
        else:
            current_app.logger.info("security.password_reset user_id=%s", user_id)
            if current_user.user_id == user_id:
                logout_user(); session.clear()
                return redirect(url_for("auth.login"), code=303)
            return redirect(url_for("admin.index"), code=303)
    return render_template("auth/password.html", form=form, error=error,
                           heading="重置账号密码", target_username=target.username)
