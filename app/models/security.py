"""Credential-free audit snapshots, independent of the service layer."""

import json
import re
from collections.abc import Mapping


def _is_credential_key(key) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return (
        any(word in normalized for word in ("password", "passwd", "token", "secret", "credential"))
        or normalized in {
            "pwd", "key", "apikey", "privatekey", "publickey", "accesskey",
            "signingkey", "encryptionkey", "authorization", "authorizationheader",
            "cookie", "cookies", "sessionid", "sessioncookie",
        }
    )


def _clean_snapshot(value):
    if isinstance(value, Mapping):
        return {
            key: _clean_snapshot(item)
            for key, item in value.items()
            if not _is_credential_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [_clean_snapshot(item) for item in value]
    return value


def sanitize_snapshot(value):
    """Copy finite JSON data and recursively remove credential fields.

    SQLite's JSON serializer otherwise accepts NaN and Infinity. Reject those
    and unsupported Python objects before a service adds an invalid audit log.
    """
    try:
        cleaned = _clean_snapshot(value)
        json.dumps(cleaned, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Audit snapshots must contain finite JSON data") from exc
    return cleaned
