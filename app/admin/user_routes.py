from flask import render_template, request, url_for
from flask_login import current_user
from wtforms.fields import SelectChoice

from app.services import user_management_service as service
from app.services.permission_service import role_required
from . import bp
from .archive_forms import ConfirmForm
from .archive_views import editor, list_params, load, set_choices, strict_form
from .user_forms import CreateUserForm, UserForm


@bp.get("/users")
@role_required("admin")
def users():
    role, active = request.args.get("role", ""), request.args.get("active", "")
    page = load(service.list_users, role=role, active=active, **list_params())
    return render_template("admin/user_list.html", page=page, roles=service.ROLE_LABELS, role=role, active=active)


@bp.get("/users/<int:user_id>")
@role_required("admin")
def user_detail(user_id):
    return render_template("admin/user_detail.html", account=load(service.get_user, user_id),
                           roles=service.ROLE_LABELS)


def _editor(account=None):
    fields = service.EDIT_FIELDS if account is not None else service.CREATE_FIELDS
    strict_form(*fields)
    options = load(service.account_choices, user_id=account.user_id if account is not None else None)
    if account is None:
        form = CreateUserForm()
        back = url_for("admin.users")
    else:
        form = UserForm(data={"username": account.username, "role": account.role.name,
                              "student_id": account.student_id, "teacher_id": account.teacher_id})
        back = url_for("admin.user_detail", user_id=account.user_id)
    choices = options["roles"]
    if account is None:
        choices = [("", "请选择角色"), *choices]
    elif account.user_id == current_user.user_id:
        choices = [("admin", service.ROLE_LABELS["admin"])]
        options["student_id"] = options["teacher_id"] = []
    form.role.choices = [SelectChoice(value=key, label=label) for key, label in choices]
    set_choices(form, "student_id", options["student_id"])
    set_choices(form, "teacher_id", options["teacher_id"])

    def save():
        values = {field: form[field].data for field in fields}
        for name in ("student_id", "teacher_id"):
            values[name] = values[name] or None
        if account is None:
            return service.create_user(current_user, values)
        return service.update_user(current_user, account.user_id, values)

    return editor(form, title="创建账号" if account is None else "编辑账号", operation=save, back_url=back,
                  success_url=lambda row: url_for("admin.user_detail", user_id=row.user_id),
                  note="教师和学生请选择对应档案。管理员请将两项档案都设为暂不指定。")


@bp.route("/users/new", methods=["GET", "POST"])
@role_required("admin")
def user_new():
    return _editor()


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def user_edit(user_id):
    return _editor(load(service.get_user, user_id))


def _set_status(user_id, active):
    account = load(service.get_user, user_id)
    strict_form("confirm")
    form = ConfirmForm()
    back = url_for("admin.user_detail", user_id=user_id)
    return editor(form, title="启用账号" if active else "停用账号", back_url=back,
                  operation=lambda: service.set_user_active(current_user, user_id, active),
                  success_url=lambda _: back,
                  note=f"账号 {account.username}。启停只影响登录权限。")


@bp.route("/users/<int:user_id>/activate", methods=["GET", "POST"])
@role_required("admin")
def user_activate(user_id):
    return _set_status(user_id, True)


@bp.route("/users/<int:user_id>/deactivate", methods=["GET", "POST"])
@role_required("admin")
def user_deactivate(user_id):
    return _set_status(user_id, False)
