"""Administrator account operations. The caller commits account and audit together."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Role, Student, Teacher, User
from .archive_common import (
    ArchiveValidationError, begin_archive_write, check_fields, check_unique, get_record, optional_relation,
    pagination, search_term, text_value,
)
from .audit_service import record_create, record_status_change, record_update
from .data_validation_service import validate_user_profile_binding
from .permission_service import require_current_admin

ROLE_LABELS = {"admin": "管理员", "teacher": "教师", "student": "学生"}
EDIT_FIELDS = ("username", "role", "student_id", "teacher_id")
CREATE_FIELDS = (*EDIT_FIELDS, "password", "confirm_password")


def list_users(actor, *, q="", role="", active="", page=1, per_page=20):
    require_current_admin(actor)
    q = search_term(q)
    statement = select(User).join(Role).options(
        selectinload(User.role), selectinload(User.student), selectinload(User.teacher)
    )
    if q:
        statement = statement.where(User.username.contains(q, autoescape=True))
    if role:
        if not isinstance(role, str) or role not in ROLE_LABELS:
            raise ArchiveValidationError("role", "角色无效。")
        statement = statement.where(Role.name == role)
    if active:
        if active not in ("0", "1"):
            raise ArchiveValidationError("active", "启用状态无效。")
        statement = statement.where(User.is_active.is_(active == "1"))
    return pagination(statement.order_by(User.username, User.user_id), page=page, per_page=per_page)


def get_user(actor, user_id):
    require_current_admin(actor)
    return get_record(User, user_id)


def account_choices(actor, *, user_id=None):
    require_current_admin(actor)
    roles = db.session.scalars(select(Role.name).where(Role.name.in_(ROLE_LABELS)).order_by(Role.role_id)).all()
    options = {"roles": [(name, ROLE_LABELS[name]) for name in roles]}
    for field, model, code_column in (
        ("student_id", Student, Student.student_no),
        ("teacher_id", Teacher, Teacher.teacher_no),
    ):
        key = getattr(model, field)
        binding = getattr(User, field)
        used = select(binding).where(binding.is_not(None))
        if user_id is not None:
            used = used.where(User.user_id != user_id)
        rows = db.session.execute(select(key, code_column, model.name).where(key.not_in(used)).order_by(code_column))
        options[field] = [(identity, f"{code} · {name}") for identity, code, name in rows]
    return options


def _begin_admin_write(actor):
    require_current_admin(actor)
    begin_archive_write()
    require_current_admin(actor)


def _account_values(data, user_id=None):
    username = text_value(data, "username", 50, required=True).strip()
    role = data.get("role")
    if not isinstance(role, str) or role not in ROLE_LABELS:
        raise ArchiveValidationError("role", "请选择支持的角色。")
    role_row = db.session.scalar(select(Role).where(Role.name == role))
    if role_row is None:
        raise ArchiveValidationError("role", "该角色尚未初始化。")
    student_id, teacher_id = data.get("student_id"), data.get("teacher_id")
    if (student_id is not None, teacher_id is not None) != (role == "student", role == "teacher"):
        raise ArchiveValidationError("role", "角色与档案绑定不匹配，请仅选择对应档案。")
    student = optional_relation(Student, student_id, "student_id")
    teacher = optional_relation(Teacher, teacher_id, "teacher_id")
    check_unique(User, "username", username, excluding=user_id)
    if student is not None:
        check_unique(User, "student_id", student.student_id, excluding=user_id)
    if teacher is not None:
        check_unique(User, "teacher_id", teacher.teacher_id, excluding=user_id)
    return {"username": username, "role": role_row, "student": student, "teacher": teacher}


def _snapshot(user):
    return {"username": user.username, "role": user.role.name, "student_id": user.student_id,
            "teacher_id": user.teacher_id, "is_active": user.is_active}


def _preserve_admin(actor, target, *, role, enabled):
    if target.user_id == actor.user_id and (not enabled or role != "admin"):
        raise PermissionError("Administrator cannot disable or remove their own access")
    if target.is_active and target.role.name == "admin" and (not enabled or role != "admin"):
        remaining = db.session.scalar(select(func.count(User.user_id)).join(Role).where(
            User.user_id != target.user_id, User.is_active.is_(True), Role.name == "admin",
            User.teacher_id.is_(None), User.student_id.is_(None),
        ))
        if not remaining:
            raise ArchiveValidationError(None, "必须保留至少一个可用管理员。")


def create_user(actor, data):
    check_fields(data, CREATE_FIELDS)
    password = data.get("password")
    if not isinstance(password, str) or not 1 <= len(password) <= 1024:
        raise ArchiveValidationError("password", "请输入有效密码，长度最多 1024 个字符。")
    if password != data.get("confirm_password"):
        raise ArchiveValidationError("confirm_password", "两次密码不一致。")
    require_current_admin(actor)
    password_hash = generate_password_hash(password)
    _begin_admin_write(actor)
    target = User(**_account_values(data), password_hash=password_hash, is_active=True)
    db.session.add(target)
    validate_user_profile_binding(target)
    db.session.flush()
    record_create("User", target.user_id, actor_user_id=actor.user_id, after_data=_snapshot(target))
    return target


def update_user(actor, user_id, data):
    check_fields(data, EDIT_FIELDS)
    _begin_admin_write(actor)
    target = get_record(User, user_id, fresh=True)
    values = _account_values(data, target.user_id)
    _preserve_admin(actor, target, role=values["role"].name, enabled=target.is_active)
    before = _snapshot(target)
    for key, value in values.items():
        setattr(target, key, value)
    validate_user_profile_binding(target)
    db.session.flush()
    after = _snapshot(target)
    if before != after:
        after["identity_changed"] = any(before[key] != after[key] for key in ("role", "student_id", "teacher_id"))
        record_update("User", target.user_id, actor_user_id=actor.user_id, before_data=before, after_data=after)
    return target


def set_user_active(actor, user_id, enabled):
    if type(enabled) is not bool:
        raise ArchiveValidationError(None, "启用状态无效。")
    _begin_admin_write(actor)
    target = get_record(User, user_id, fresh=True)
    _preserve_admin(actor, target, role=target.role.name, enabled=enabled)
    if enabled:
        try:
            validate_user_profile_binding(target)
        except ValueError as error:
            raise ArchiveValidationError(None, "角色与档案绑定无效，无法启用。") from error
    if target.is_active == enabled:
        return target
    before = _snapshot(target)
    target.is_active = enabled
    db.session.flush()
    record_status_change("User", target.user_id, actor_user_id=actor.user_id,
                         before_data=before, after_data=_snapshot(target))
    return target
