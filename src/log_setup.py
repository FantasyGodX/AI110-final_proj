"""Logging for VibeFinder. Every agent step is written to logs/vibefinder.log.

Warnings and errors also go to the console. Importing this module never fails:
if the log file cannot be created the logger falls back to console only.
"""

import logging
import os

LOG_PATH = os.path.join("logs", "vibefinder.log")
_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"


def get_logger(name: str = "vibefinder") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(file_handler)
    except OSError as err:  # read-only folder, etc.
        logger.warning("file logging disabled: %s", err)
    return logger
