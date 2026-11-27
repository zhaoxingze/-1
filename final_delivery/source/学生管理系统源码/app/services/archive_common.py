"""Shared archive validation and auditing; callers own the transaction."""

from datetime import date, datetime
from collections.abc import Mapping
from functools import wraps
import re

from sqlalchemy import inspect, select

from app.extensions import db
from . import audit_service
from .permission_service import has_role

MAX_ID = 9223372036854775807


class ArchiveValidationError(ValueError):
    def __init__(self, field, message):
        self.field = field
        super().__init__(message)


def require_admin(actor):
    if not has_role(actor, "admin"):
        raise PermissionError("Administrator required")


def archive_write(operation):
    """Acquire SQLite's writer lock before reading mutable business state.

    Python's legacy SQLite transaction mode does not begin a DB transaction
    for SELECT. A cached object can otherwise outlive a different writer's
    commit. Reuse an existing write transaction for composed service calls;
    the caller still owns commit/rollback.
    """
    @wraps(operation)
    def guarded(actor, *args, **kwargs):
        require_admin(actor)
        begin_archive_write()
        return operation(actor, *args, **kwargs)
    return guarded


def begin_archive_write():
    """Reserve the SQLite writer before reading state used by the write."""
    connection = db.session.connection()
    if connection.dialect.name == "sqlite" and not connection.connection.dbapi_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def check_fields(data, allowed):
    if not isinstance(data, Mapping) or set(data) - set(allowed):
        raise ArchiveValidationError(None, "提交了不支持的档案字段。")


def text_value(data, field, maximum, *, required=False):
    value = data.get(field)
    if value is None or value == "":
        if required:
            raise ArchiveValidationError(field, "此项不能为空。")
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ArchiveValidationError(field, f"请输入有效内容，长度不超过{maximum}个字符。")
    return value


def date_value(data, field, *, required=False):
    value = data.get(field)
    if value is None or value == "":
        if required:
            raise ArchiveValidationError(field, "请选择有效日期。")
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ArchiveValidationError(field, "日期格式或日历日期无效。")


def identifier(value):
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 19:
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_ID:
        raise LookupError("Record does not exist")
    return value


def get_record(model, identity, *, fresh=False):
    identity = identifier(identity)
    with db.session.no_autoflush:
        row = db.session.get(model, identity, populate_existing=fresh)
    if row is None:
        raise LookupError("Record does not exist")
    return row


def optional_relation(model, value, field):
    if value is None or value == "":
        return None
    try:
        return get_record(model, value, fresh=True)
    except LookupError as exc:
        raise ArchiveValidationError(field, "关联档案不存在或编号无效。") from exc


def check_unique(model, column, value, *, excluding=None):
    pk = inspect(model).primary_key[0]
    statement = select(pk).where(getattr(model, column) == value)
    if excluding is not None:
        statement = statement.where(pk != excluding)
    with db.session.no_autoflush:
        if db.session.scalar(statement) is not None:
            raise ArchiveValidationError(column, "该编号已存在，请使用其他编号。")


def email_value(data):
    value = text_value(data, "email", 100)
    if value and not re.fullmatch(r"[^@\s]+@[^@\s]+", value):
        raise ArchiveValidationError("email", "请输入有效的邮箱地址。")
    return value


def snapshot(row, fields):
    values = {field: getattr(row, field) for field in fields}
    return {key: value.isoformat() if isinstance(value, (date, datetime)) else value for key, value in values.items()}


def audit(actor, row, fields, *, before=None, action="update"):
    # Explicit domain field lists never serialize User or credential objects.
    identity = getattr(row, inspect(type(row)).primary_key[0].key)
    return audit_service.record_audit(type(row).__name__, identity, action=action,
        actor_user_id=actor.user_id, before_data=before, after_data=snapshot(row, fields))


def pagination(statement, *, page=1, per_page=20):
    if (isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= 2147483647
            or isinstance(per_page, bool) or not isinstance(per_page, int) or not 1 <= per_page <= 100):
        raise ArchiveValidationError(None, "分页参数无效。")
    return db.paginate(statement, page=page, per_page=per_page, max_per_page=100, error_out=True)


def search_term(value):
    if not isinstance(value, str) or len(value) > 100:
        raise ArchiveValidationError(None, "搜索内容不能超过100个字符。")
    return value.strip()
