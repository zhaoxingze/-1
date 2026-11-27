"""Credential updates and append-only audit share the caller's transaction."""

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User
from .audit_service import record_update
from .permission_service import has_role
from .data_validation_service import validate_user_profile_binding


def _check_actor(actor, password):
    if not has_role(actor, "admin", "teacher", "student"):
        raise PermissionError("Account is not authorized")
    if not isinstance(password, str) or not 1 <= len(password) <= 1024:
        raise ValueError("当前密码验证失败。")
    try:
        matches = check_password_hash(actor.password_hash, password)
    except (TypeError, ValueError):
        matches = False
    if not matches:
        raise ValueError("当前密码验证失败。")


def _update(actor, target, new_password, operation):
    if not isinstance(new_password, str) or not 1 <= len(new_password) <= 1024:
        raise ValueError("新密码不能为空且不能超过 1024 个字符。")
    validate_user_profile_binding(target)
    target.password_hash = generate_password_hash(new_password)
    # The existing sanitizer removes keys containing 'password', including
    # innocent boolean labels. Record only a non-secret operation marker.
    record_update("User", target.user_id, actor_user_id=actor.user_id,
                  after_data={"operation": operation, "changed": True})


def change_own_password(actor: User, current_password: str, new_password: str) -> User:
    _check_actor(actor, current_password)
    _update(actor, actor, new_password, "self_change")
    return actor


def reset_user_password(actor: User, target_user_id: int, actor_password: str, new_password: str) -> User:
    if not has_role(actor, "admin"):
        raise PermissionError("Administrator required")
    _check_actor(actor, actor_password)
    if isinstance(target_user_id, bool) or not isinstance(target_user_id, int):
        raise ValueError("Invalid user identity")
    target = db.session.get(User, target_user_id)
    if target is None:
        raise LookupError("User does not exist")
    _update(actor, target, new_password, "admin_reset")
    return target
