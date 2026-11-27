"""Console logging suitable for the local development skeleton."""

import logging

from flask import Flask
from flask.logging import default_handler


def configure_logging(app: Flask) -> None:
    logger = app.logger
    logger.setLevel(app.config["LOG_LEVEL"])
    if default_handler in logger.handlers:
        default_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
