"""Stage 1 contracts for the application factory."""

from importlib.util import find_spec

from flask import Flask


def test_application_can_be_created():
    # A missing application package is reported as a meaningful initial failure.
    assert find_spec("app") is not None, "The Flask application factory is not implemented yet."
    from app import create_app

    application = create_app("testing")
    assert isinstance(application, Flask)
    assert application.testing is True
