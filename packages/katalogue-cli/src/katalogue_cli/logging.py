"""Logging configuration for the Katalogue CLI.

Call configure_logging() once at CLI startup. Library code (katalogue-sdk)
uses getLogger(__name__) only and never calls configure_logging().
"""

from __future__ import annotations

import logging

_FORMAT = "%(name)s %(levelname)s %(message)s"

# Third-party libraries that log sensitive data (e.g. full token responses)
# at DEBUG level. Always kept at WARNING regardless of --verbose.
_NOISY_LOGGERS = (
    "oauthlib",
    "requests_oauthlib",
    "urllib3",
)


def configure_logging(verbose: bool) -> None:
    """Configure root logging for the CLI process.

    Args:
        verbose: When True, sets the root logger to DEBUG so katalogue-sdk
            and katalogue-cli internals emit diagnostic output. Third-party
            libraries that log sensitive data are always capped at WARNING.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format=_FORMAT)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
