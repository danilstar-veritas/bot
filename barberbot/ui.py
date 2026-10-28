"""Спільне для екранів бота: помилка «кнопка застаріла» і розбір даних кнопок."""

from __future__ import annotations

from datetime import date, datetime, time


class Expired(Exception):
    """Кнопка застаріла або містить неправильні дані."""


def _d(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except (ValueError, TypeError):
        raise Expired() from None


def _t(value: str) -> time:
    try:
        return datetime.strptime(value, "%H%M").time()
    except (ValueError, TypeError):
        raise Expired() from None


def _int(value: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        raise Expired() from None


def _opt(parts: list[str], i: int) -> str | None:
    """Необов'язкова частина даних кнопки (наприклад, новий майстер у кінці)."""
    return parts[i] if len(parts) > i and parts[i] else None


def _rows(buttons: list[dict], per_row: int) -> list[list[dict]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]
