"""
core/validator.py
~~~~~~~~~~~~~~~~~
Input validation for ZeroForge.

All functions raise InvalidTaskError (or a sub-exception) when validation
fails.  They return the validated (and coerced) value on success.

Keeping validation separate from the model keeps the model clean and makes
it easy to test validation independently.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.models import Priority, TaskStatus
from utils.errors import InvalidTaskError, InvalidDateError
from utils.dates import parse_date


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

MAX_TITLE_LENGTH = 200


def validate_title(title: str) -> str:
    """
    Validate and normalise a task title.

    Rules:
    - Must be a non-empty string after stripping whitespace.
    - Maximum 200 characters.
    """
    if not isinstance(title, str):
        raise InvalidTaskError("Title must be a string.")
    title = title.strip()
    if not title:
        raise InvalidTaskError("Title must not be empty.")
    if len(title) > MAX_TITLE_LENGTH:
        raise InvalidTaskError(
            f"Title is too long ({len(title)} chars). Maximum is {MAX_TITLE_LENGTH}."
        )
    return title


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------

def validate_priority(value: str) -> Priority:
    """
    Parse and validate a priority string.

    Case-insensitive.  Returns a Priority enum member.
    Raises InvalidTaskError for invalid values.
    """
    if not isinstance(value, str):
        raise InvalidTaskError("Priority must be a string.")
    try:
        return Priority.from_str(value)
    except ValueError as exc:
        raise InvalidTaskError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def validate_status(value: str) -> TaskStatus:
    """
    Parse and validate a status string.

    Accepts only persistent status values (PENDING, IN_PROGRESS, COMPLETED,
    CANCELLED).  READY and BLOCKED are derived states and are not valid here.
    """
    if not isinstance(value, str):
        raise InvalidTaskError("Status must be a string.")
    try:
        return TaskStatus.from_str(value)
    except ValueError as exc:
        raise InvalidTaskError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Estimated minutes
# ---------------------------------------------------------------------------

def validate_estimated_minutes(value) -> int:
    """
    Validate an effort estimate.

    Must be a positive integer (> 0).
    Accepts int or string representations.
    """
    try:
        mins = int(value)
    except (TypeError, ValueError):
        raise InvalidTaskError(
            f"Estimated minutes must be a positive integer, got '{value}'."
        )
    if mins <= 0:
        raise InvalidTaskError(
            f"Estimated minutes must be greater than 0, got {mins}."
        )
    return mins


# ---------------------------------------------------------------------------
# Due date
# ---------------------------------------------------------------------------

def validate_due_date(value: str) -> datetime:
    """
    Parse and validate a due date string.

    Delegates to utils.dates.parse_date which understands several ISO-8601
    variants.  Raises InvalidTaskError wrapping InvalidDateError on failure.
    """
    if not isinstance(value, str):
        raise InvalidTaskError("Due date must be a string.")
    try:
        return parse_date(value)
    except InvalidDateError as exc:
        raise InvalidTaskError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Task ID
# ---------------------------------------------------------------------------

def validate_task_id(value) -> int:
    """
    Validate a task ID argument from the CLI.

    Must be a positive integer.
    """
    try:
        tid = int(value)
    except (TypeError, ValueError):
        raise InvalidTaskError(f"Task ID must be a positive integer, got '{value}'.")
    if tid <= 0:
        raise InvalidTaskError(f"Task ID must be greater than 0, got {tid}.")
    return tid


# ---------------------------------------------------------------------------
# Description
# ---------------------------------------------------------------------------

MAX_DESCRIPTION_LENGTH = 2000


def validate_description(value: str) -> str:
    """
    Validate and normalise an optional task description.

    Allows empty strings.  Strips leading/trailing whitespace.
    """
    if not isinstance(value, str):
        raise InvalidTaskError("Description must be a string.")
    value = value.strip()
    if len(value) > MAX_DESCRIPTION_LENGTH:
        raise InvalidTaskError(
            f"Description is too long ({len(value)} chars). Maximum is {MAX_DESCRIPTION_LENGTH}."
        )
    return value
