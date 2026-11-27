"""Copy a consistent SQLite snapshot and verify it as an independent file."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time


def _existing_database(path):
    database = Path(path).resolve(strict=True)
    with database.open("rb") as file:
        if file.read(16) != b"SQLite format 3\x00":
            raise ValueError("Source is not a SQLite database.")
    return database


def _check_database(connection):
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed.")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("SQLite foreign key check failed.")


def verify_database(path):
    database = _existing_database(path)
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
        _check_database(connection)
    with database.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    return {"file": database.name, "integrity_check": "ok", "foreign_key_violations": 0,
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "bytes": database.stat().st_size, "sha256": digest}


def copy_database(source, destination):
    source = _existing_database(source)
    destination = Path(destination).resolve()
    if any(Path(f"{destination}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal")):
        raise FileExistsError("Destination SQLite sidecar exists.")
    with destination.open("xb"):
        pass
    deadline = time.monotonic() + 30

    def check_progress(status, remaining, total):
        if remaining and time.monotonic() > deadline:
            raise TimeoutError("SQLite backup did not finish within 30 seconds.")

    try:
        with (closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=5)) as reader,
              closing(sqlite3.connect(destination, timeout=5)) as writer):
            reader.backup(writer, pages=256, progress=check_progress)
            # Ensure the portable result requires only this one file.
            if writer.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                raise ValueError("Could not store the result as a standalone database.")
        report = verify_database(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore"):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        command.add_argument("destination", type=Path)
    commands.add_parser("verify").add_argument("database", type=Path)
    args = parser.parse_args(argv)
    try:
        report = (verify_database(args.database) if args.command == "verify"
                  else copy_database(args.source, args.destination))
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"{args.command} failed: {error}\n")
    print(json.dumps({"operation": args.command, **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
