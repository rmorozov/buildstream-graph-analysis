"""
Logging setup for bga.

Every package module obtains its logger via `logging.getLogger(__name__)`,
so they all nest under the single "bga" logger. Handlers are attached only
to "bga" itself (never the root logger) - child loggers propagate up to it
by default, so setting "bga"'s level here is sufficient to control every
module without touching each one individually.
"""
import logging
import sys
from typing import Optional

_FORMAT = "%(levelname)s %(name)s: %(message)s"


def configure_logging(
    verbose: bool = False,
    quiet: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure the "bga" logger tree.

    verbose -> DEBUG, quiet -> ERROR, neither -> WARNING (the default).
    verbose and quiet are mutually exclusive at the CLI argument-parsing
    level; if both are somehow set, quiet (the more conservative choice)
    wins.
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logger = logging.getLogger("bga")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(_FORMAT)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
