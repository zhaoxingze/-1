"""Database datetimes are UTC with the timezone marker removed."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    """Return an unambiguous UTC naive timestamp for database defaults."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UTCNaiveDateTime(TypeDecorator):
    """Normalize aware inputs at the storage boundary; preserve naive UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("DATETIME values must be datetime objects")
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
