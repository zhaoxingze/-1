"""Unbound extensions shared by application factory instances."""

import sqlite3

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate(compare_type=True, render_as_batch=True)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, connection_record):
    """SQLite foreign keys are connection-local, including temporary test DBs."""
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            # REPLACE deletes a conflicting row before inserting. Recursive
            # triggers ensure that deletion cannot bypass append-only guards.
            cursor.execute("PRAGMA recursive_triggers=ON")
        finally:
            cursor.close()
