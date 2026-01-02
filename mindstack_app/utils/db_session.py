"""Utility helpers for working with the SQLAlchemy session.

These helpers focus on improving the resilience of commits when the
application is backed by SQLite.  SQLite places a write lock on the
database
for the duration of a transaction which can occasionally surface as a
``database is locked`` error when two requests try to touch the database at
roughly the same time.  The :func:`safe_commit` helper retries the commit
with
exponential backoff so short lived locks are retried transparently.
"""

from __future__ import annotations

import time

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.session import Session

LOCKED_MESSAGES = {"database is locked", "database is busy"}


def _is_lock_error(error: OperationalError) -> bool:
    """Return ``True`` if the OperationalError was caused by a lock."""

    message = str(error).lower()
    return any(token in message for token in LOCKED_MESSAGES)


def safe_commit(
    session: Session,
    retries: int = 5,
    initial_delay: float = 0.1,
) -> None:
    """Commit the current transaction, retrying when SQLite is locked.

    Args:
        session: The SQLAlchemy session to commit.
        retries: Maximum number of attempts before the error is re-raised.
        initial_delay: The delay (in seconds) before the first retry.  The
            delay is doubled after every attempt.

    Raises:
        OperationalError: Re-raised if the session cannot be committed after
            the configured number of retries or if the error is unrelated to
            SQLite locking.
    """

    delay = initial_delay
    for attempt in range(retries):
        try:
            session.commit()
            return
        except OperationalError as exc:  # pragma: no cover - retriable path
            session.rollback()
            if attempt == retries - 1 or not _is_lock_error(exc):
                raise

            time.sleep(delay)
            delay *= 2

