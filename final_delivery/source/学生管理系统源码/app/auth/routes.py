"""Web login/logout; credentials never reach templates or ordinary logs."""

import secrets
import time

from flask import current_app, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User
from . import bp
from .forms import ChangePasswordForm, LoginForm
from .session import account_is_usable, credential_version, safe_next

_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))
LOGIN_FAILURE = "用户名或密码错误，或账号不可用。"


def password_matches(stored_hash: str, password: str) -> bool:
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.workbench"))
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == form.username.data))
        password_valid = password_matches(user.password_hash if user else _DUMMY_HASH, form.password.data)
        if password_valid and account_is_usable(user):
            session.clear()
            login_user(user, remember=False, fresh=True)
            session.permanent = True
            session["_auth_issued_at"] = time.time()
            session["_auth_version"] = credential_version(user)
            current_app.logger.info("security.login_success user_id=%s", user.user_id)
            return redirect(safe_next(request.args.get("next")) or url_for("dashboard.workbench"), code=303)
        current_app.logger.info("security.login_failure")
        error = LOGIN_FAILURE
    return render_template("auth/login.html", form=form, error=error)


@bp.post("/logout")
def logout():
    logout_user()
    session.clear()
    current_app.logger.info("security.logout")
    return redirect(url_for("auth.login"), code=303)


@bp.route("/password/change", methods=["GET", "POST"])
@login_required
def change_password():
    from app.services.password_service import change_own_password

    form = ChangePasswordForm()
    error = None
    if form.validate_on_submit():
        try:
            change_own_password(current_user, form.current_password.data, form.new_password.data)
            db.session.commit()
        except (ValueError, PermissionError):
            db.session.rollback()
            error = "当前密码验证失败或新密码无效。"
        except SQLAlchemyError:
            db.session.rollback()
            # Never include SQL parameters or the exception: they can contain a hash.
            current_app.logger.error("security.password_change_storage_failure")
            error = "密码更新失败，请稍后重试。"
        else:
            logout_user(); session.clear()
            current_app.logger.info("security.password_changed")
            return redirect(url_for("auth.login"), code=303)
    return render_template("auth/password.html", form=form, error=error, heading="修改本人密码")
