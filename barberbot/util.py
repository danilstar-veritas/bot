"""Дрібні допоміжні функції."""

from __future__ import annotations

import re
from datetime import date, datetime, time

AFFIRMATIVE = {
    "так", "да", "ага", "угу", "ок", "окей", "ok", "okay", "yes", "yep", "yeah", "sure", "y", "+", "👍", "✅",
    "підтверджую", "подтверждаю", "confirm", "згоден", "згодна", "согласен", "согласна", "давай", "давайте",
    "добре", "хорошо", "супер", "чудово", "отлично", "звісно", "конечно", "igen", "jó", "записуй", "записывай",
}


def normalize_phone(text: str, from_contact: bool = False) -> str | None:
    """Повертає номер у вигляді «+380501234567» / «0501234567» або None, якщо це не номер."""
    if not text:
        return None
    raw = text.strip()
    if re.search(r"[^\d\s+()\-.]", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if not 9 <= len(digits) <= 15:
        return None
    plus = raw.lstrip().startswith("+") or (from_contact and len(digits) >= 11)
    return ("+" if plus else "") + digits


POLITE = {
    "дякую", "дякуємо", "спасибі", "спасибо", "thanks", "thank", "you", "please", "будь", "ласка", "пожалуйста",
    "все", "всё", "вірно", "правильно", "верно", "correct", "right", "так", "да", "звісно", "конечно",
}


def is_affirmative(text: str) -> bool:
    """«так», «так, дякую», «yes please» — коротке підтвердження без жодних уточнень.

    «так, але о 18» чи «так, о 18:00» — НЕ підтвердження (є інші слова/цифри).
    """
    if not text:
        return False
    cleaned = re.sub(r"[!.,?)(:;]+", " ", text.lower()).split()
    if not cleaned or len(cleaned) > 4:
        return False
    if cleaned[0] not in AFFIRMATIVE:
        return False
    return all(w in AFFIRMATIVE or w in POLITE for w in cleaned[1:])


def parse_date_arg(value) -> date | None:
    if value is None:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y.%m.%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_time_arg(value) -> time | None:
    if value is None:
        return None
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})\s*$", str(value))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return time(h, mi)
    return None


def clean_ai_text(text: str) -> str:
    """Прибирає markdown, який модель могла додати попри інструкції."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
