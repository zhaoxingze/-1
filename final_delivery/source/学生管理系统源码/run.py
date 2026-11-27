"""Loopback launcher for development and classroom demonstrations."""

import os
from pathlib import Path

from app import create_app

profile = os.environ.get("APP_ENV", "development")
instance = os.environ.get("SMS_INSTANCE_PATH")
app = create_app(profile, instance_path=str(Path(instance).expanduser().resolve()) if instance else None)

if __name__ == "__main__":
    if profile == "production":
        raise SystemExit("Production requires an HTTPS deployment with a production WSGI server.")
    if profile == "demo":
        port = os.environ.get("DEMO_PORT", "8000")
        if not port.isascii() or not port.isdecimal() or len(port) > 5 or not 1 <= int(port) <= 65535:
            raise SystemExit("DEMO_PORT must be an integer from 1 to 65535.")
        app.run(host="127.0.0.1", port=int(port), debug=False, use_debugger=False, use_reloader=False)
    else:
        app.run(host="127.0.0.1", port=5000, use_reloader=False)
