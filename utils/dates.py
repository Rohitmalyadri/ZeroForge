"""
utils/dates.py
~~~~~~~~~~~~~~
Date and time utilities for ZeroForge.

Strategy:
- All internal timestamps are stored as UTC ISO-8601 strings in SQLite.
- Datetime objects used internally are timezone-aware (UTC).
- Deadlines entered by the user as YYYY-MM-DD are treated as end-of-day UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from utils.errors import InvalidDateError

# Accepted input formats for parsing user-supplied date strings.
_INPUT_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]

# The canonical format used to store datetimes in SQLite.
_STORAGE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def parse_date(value: str) -> datetime:
    """
    Parse a user-supplied date/datetime string into a UTC-aware datetime.

    If only a date (YYYY-MM-DD) is supplied, the time is set to end-of-day
    (23:59:59 UTC) so the deadline is inclusive of that calendar day.

    Raises InvalidDateError for unrecognised formats.
    """
    value = value.strip()
    for fmt in _INPUT_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            # If the user only supplied a date (no time), use end-of-day.
            if fmt == "%Y-%m-%d":
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise InvalidDateError(value)


def to_storage_str(dt: datetime) -> str:
    """
    Convert a datetime to the canonical storage string (UTC, no tz suffix).
    The tz offset is intentionally stripped because SQLite stores plain text
    and we document the convention that all stored times are UTC.
    """
    # Normalise to UTC first.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime(_STORAGE_FORMAT)


def from_storage_str(value: str) -> datetime:
    """
    Parse a storage string back to a UTC-aware datetime.
    Returns a timezone-aware datetime in UTC.
    """
    try:
        dt = datetime.strptime(value, _STORAGE_FORMAT)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise StorageError(f"Cannot parse stored timestamp '{value}'") from exc


def format_display(dt: Optional[datetime]) -> str:
    """Format a datetime for human display.  Returns '-' for None."""
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def is_overdue(dt: Optional[datetime], now: Optional[datetime] = None) -> bool:
    """Return True if *dt* is in the past relative to *now* (default: UTC now)."""
    if dt is None:
        return False
    if now is None:
        now = now_utc()
    return dt < now


def deadline_urgency_score(dt: Optional[datetime], now: Optional[datetime] = None) -> float:
    """
    Return a numeric urgency score for ranking purposes.

    Lower score = more urgent (sorts earlier).
    Tasks without a deadline get +infinity so they rank after all deadline tasks.

    For overdue tasks the score is negative (even more urgent).
    """
    if dt is None:
        return float("inf")
    if now is None:
        now = now_utc()
    delta = dt - now  # negative if overdue
    return delta.total_seconds()


# Avoid circular import — StorageError is referenced in from_storage_str.
from utils.errors import StorageError  # noqa: E402
