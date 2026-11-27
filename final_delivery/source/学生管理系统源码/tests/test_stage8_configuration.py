import runpy

import pytest
from flask import Flask

from app import create_app


def test_demo_has_random_keys_and_http_security_without_debug(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "ignored-synthetic-setting")
    monkeypatch.setenv("FLASK_DEBUG", "1")
    first = create_app("demo", {"DEBUG": True}, instance_path=str(tmp_path / "one"))
    second = create_app("demo", instance_path=str(tmp_path / "two"))
    assert not first.debug and not first.testing
    assert first.secret_key != second.secret_key
    assert first.secret_key != "ignored-synthetic-setting" and len(bytes.fromhex(first.secret_key)) == 32
    assert first.config["SESSION_COOKIE_HTTPONLY"] and first.config["WTF_CSRF_ENABLED"]
    assert first.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert not first.config["SESSION_COOKIE_SECURE"]
    client = first.test_client()
    assert client.get("/health", base_url="http://127.0.0.1:8040").status_code == 200
    assert client.get("/health", base_url="http://unexpected.example").status_code == 400


def test_direct_run_forces_loopback_and_debugger_off(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.setenv("DEMO_PORT", "8048")
    monkeypatch.setenv("SMS_INSTANCE_PATH", str(tmp_path / "demo"))
    monkeypatch.delenv("SMS_DATABASE_URI", raising=False)
    calls = []

    def capture(application, **options):
        calls.append((application.debug, application.instance_path, options))

    monkeypatch.setattr(Flask, "run", capture)
    runpy.run_module("run", run_name="__main__")
    assert calls == [(False, str(tmp_path / "demo"),
                      {"host": "127.0.0.1", "port": 8048, "debug": False,
                       "use_debugger": False, "use_reloader": False})]


@pytest.mark.parametrize("value", ["", "0", "65536", "-1", "random", "1.5"])
def test_demo_port_validation(monkeypatch, tmp_path, value):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DEMO_PORT", value)
    monkeypatch.setenv("SMS_INSTANCE_PATH", str(tmp_path))
    with pytest.raises(SystemExit, match="DEMO_PORT"):
        runpy.run_module("run", run_name="__main__")


def test_https_production_is_not_served_by_local_launcher(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "synthetic-production-configuration-fixture")
    monkeypatch.setenv("SMS_INSTANCE_PATH", str(tmp_path))
    with pytest.raises(SystemExit, match="WSGI"):
        runpy.run_module("run", run_name="__main__")
