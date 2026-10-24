"""Єдине джерело поточного часу. У тестах час можна «заморозити»."""

from __future__ import annotations

from datetime import datetime, timezone

_fixed: datetime | None = None


def utcnow() -> datetime:
    """Поточний час (aware, UTC)."""
    return _fixed if _fixed is not None else datetime.now(timezone.utc)


def set_fixed(dt: datetime | None) -> None:
    """Зафіксувати час (для тестів). dt має бути aware або None."""
    global _fixed
    if dt is not None and dt.tzinfo is None:
        raise ValueError("set_fixed очікує datetime з часовим поясом")
    _fixed = dt
