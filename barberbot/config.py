"""Читання й перевірка налаштувань.

config/settings.toml      — загальні налаштування (ключ AI, модель, ліміти)
config/tenants/*.toml     — по одному файлу на кожен заклад (бізнес-клієнта)
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import clock
from .texts import SUPPORTED_LANGS, TEXTS, WEEKDAYS_SHORT, render

ID_RE = re.compile(r"^[a-z0-9_-]{1,16}$")
SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{30,}$")
WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_OFF_WORDS = {"", "off", "-", "—", "closed", "no", "вихідний", "выходной", "x"}
RANGE_RE = re.compile(r"^\s*(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})\s*$")


class ConfigError(Exception):
    """Помилка в налаштуваннях — з поясненням, що виправити."""


# ---------------------------------------------------------------- helpers

def parse_hhmm(value: str) -> time:
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})\s*$", str(value))
    if not m:
        raise ValueError(value)
    h, mi = int(m.group(1)), int(m.group(2))
    if h == 24 and mi == 0:
        return time(23, 59)
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError(value)
    return time(h, mi)


def fmt_hhmm(t: time | datetime) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def parse_day_spec(spec, where: str) -> list[tuple[time, time]]:
    """'10:00-14:00, 15:00-19:00' -> [(10:00,14:00), (15:00,19:00)]; 'off' -> []."""
    if spec is None or spec is False:
        return []
    text = str(spec).strip().lower()
    if text in DAY_OFF_WORDS:
        return []
    result: list[tuple[time, time]] = []
    for part in re.split(r"[,;]", text):
        if not part.strip():
            continue
        m = RANGE_RE.match(part)
        if not m:
            raise ConfigError(
                f"{where}: не можу прочитати «{part.strip()}». "
                f"Приклад: \"10:00-19:00\", \"10:00-14:00, 15:00-19:00\" або \"off\" (вихідний)."
            )
        try:
            start = parse_hhmm(f"{m.group(1)}:{m.group(2)}")
            end = parse_hhmm(f"{m.group(3)}:{m.group(4)}")
        except ValueError:
            raise ConfigError(f"{where}: неправильний час у «{part.strip()}».") from None
        if end <= start:
            raise ConfigError(f"{where}: кінець має бути пізніше за початок («{part.strip()}»).")
        result.append((start, end))
    result.sort()
    for (a1, b1), (a2, b2) in zip(result, result[1:]):
        if a2 < b1:
            raise ConfigError(f"{where}: проміжки часу перетинаються.")
    return result


def parse_user_date(value: str, today: date) -> date | None:
    """Дата від людини: 2026-10-30, 30.10.2026, 30.10, 30/10, сьогодні, завтра."""
    s = str(value).strip().lower()
    if s in ("today", "сьогодні", "сегодня"):
        return today
    if s in ("tomorrow", "завтра"):
        return today + timedelta(days=1)
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.match(r"^(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?$", s)
        if m:
            d, mo = int(m.group(1)), int(m.group(2))
            if m.group(3):
                y = int(m.group(3))
                if y < 100:
                    y += 2000
                return date(y, mo, d)
            candidate = date(today.year, mo, d)
            if candidate < today - timedelta(days=31):
                candidate = date(today.year + 1, mo, d)
            return candidate
    except ValueError:
        return None
    return None


def fmt_num(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")


def _read_toml(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(f"Файл не знайдено: {path}") from None
    except UnicodeDecodeError:
        raise ConfigError(f"{path.name}: файл має бути збережений у кодуванні UTF-8.") from None
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        hint = ""
        if "“" in text or "”" in text:
            hint = (" Підказка: у файлі є «розумні» лапки “ ” — замініть їх на звичайні прямі \". "
                    "TextEdit на Mac підміняє лапки сам, тому краще редагуйте файл у VS Code.")
        raise ConfigError(f"{path.name}: помилка у форматі файлу — {e}.{hint}") from None


class _Section:
    """Зручне читання значень із перевіркою типів і зрозумілими помилками."""

    def __init__(self, data: dict | None, where: str):
        if data is not None and not isinstance(data, dict):
            raise ConfigError(f"{where}: очікувався розділ із налаштуваннями.")
        self.data = data or {}
        self.where = where

    def _err(self, key: str, msg: str) -> ConfigError:
        return ConfigError(f"{self.where} → {key}: {msg}")

    def str(self, key: str, default: str | None = "", required: bool = False) -> str:
        if key not in self.data:
            if required:
                raise self._err(key, "обов'язкове поле, заповніть його.")
            return default if default is not None else ""
        v = self.data[key]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            v = str(v)
        if not isinstance(v, str):
            raise self._err(key, "має бути текст у лапках.")
        v = v.strip()
        if required and not v:
            raise self._err(key, "обов'язкове поле, заповніть його.")
        return v

    def int(self, key: str, default: int, lo: int | None = None, hi: int | None = None) -> int:
        v = self.data.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v:
            raise self._err(key, "має бути ціле число без лапок.")
        v = int(v)
        if lo is not None and v < lo or hi is not None and v > hi:
            raise self._err(key, f"має бути від {lo} до {hi}.")
        return v

    def num(self, key: str, default: float, lo: float = 0) -> float:
        v = self.data.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise self._err(key, "має бути число без лапок.")
        if v < lo:
            raise self._err(key, f"не може бути меншим за {lo}.")
        return v

    def bool(self, key: str, default: bool) -> bool:
        v = self.data.get(key, default)
        if not isinstance(v, bool):
            raise self._err(key, "має бути true або false (без лапок).")
        return v

    def list(self, key: str, default: list | None = None) -> list:
        v = self.data.get(key, default if default is not None else [])
        if not isinstance(v, list):
            raise self._err(key, "має бути список у квадратних дужках, наприклад [1, 2].")
        return v

    def section(self, key: str) -> "_Section":
        return _Section(self.data.get(key), f"{self.where} → [{key}]")


# ---------------------------------------------------------------- settings

@dataclass
class Settings:
    anthropic_api_key: str = ""
    model: str = "claude-haiku-5-5"
    effort: str = "low"
    thinking: str = "adaptive"
    max_tokens: int = 2048
    max_tool_rounds: int = 6
    history_messages: int = 24
    history_hours: int = 24
    daily_token_limit: int = 2_000_000
    price_input: float = 0.10
    price_output: float = 0.50
    price_cache_read: float = 0.01
    price_cache_write: float = 0.125
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    telegram_api_base: str = "https://api.telegram.org"
    anthropic_api_base: str = "https://api.anthropic.com"
    scheduler_interval_sec: int = 30
    provider: str = "anthropic"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_api_base: str = "https://generativelanguage.googleapis.com"

    @property
    def ai_available(self) -> bool:
        return bool(self.gemini_api_key if self.provider == "gemini" else self.anthropic_api_key)

    @property
    def ai_model(self) -> str:
        return self.gemini_model if self.provider == "gemini" else self.model

    @property
    def ai_name(self) -> str:
        """Для повідомлень: «Ключ Anthropic не вказано» / «Ключ Gemini працює»."""
        return "Gemini" if self.provider == "gemini" else "Anthropic"

    @property
    def ai_key_field(self) -> str:
        return "gemini_api_key" if self.provider == "gemini" else "anthropic_api_key"


def load_settings(path: Path, base_dir: Path | None = None) -> Settings:
    base_dir = base_dir or path.parent.parent
    raw = _read_toml(path) if path.exists() else {}
    s = _Section(raw, path.name)
    adv = s.section("advanced")
    provider = s.str("provider", "anthropic").lower() or "anthropic"
    if provider not in ("anthropic", "gemini"):
        raise ConfigError(f"{path.name} → provider: допустимо anthropic або gemini.")
    # Безкоштовний рівень Gemini нічого не коштує, тож для нього за замовчуванням ціни нульові.
    prices = s.section("gemini_prices" if provider == "gemini" else "prices")
    default_prices = (0.0, 0.0, 0.0, 0.0) if provider == "gemini" else (0.10, 0.50, 0.01, 0.125)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip() or s.str("anthropic_api_key")
    if key and not key.startswith("sk-"):
        raise ConfigError(f"{path.name} → anthropic_api_key: ключ має починатися з «sk-». Скопіюйте його повністю.")
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or s.str("gemini_api_key")
    effort = s.str("effort", "low").lower()
    if effort not in ("low", "medium", "high", ""):
        raise ConfigError(f"{path.name} → effort: допустимо low, medium, high або \"\" (не передавати).")
    thinking = adv.str("thinking", "adaptive").lower()
    if thinking not in ("adaptive", "disabled"):
        raise ConfigError(f"{path.name} → thinking: допустимо adaptive або disabled.")
    data_dir = Path(adv.str("data_dir", "data") or "data")
    if not data_dir.is_absolute():
        data_dir = base_dir / data_dir
    return Settings(
        anthropic_api_key=key,
        model=s.str("model", "claude-haiku-5-5") or "claude-haiku-5-5",
        effort=effort,
        thinking=thinking,
        daily_token_limit=s.int("daily_token_limit", 2_000_000, 0, 10**10),
        max_tokens=adv.int("max_tokens", 2048, 256, 32000),
        max_tool_rounds=adv.int("max_tool_rounds", 6, 1, 20),
        history_messages=adv.int("history_messages", 24, 2, 200),
        history_hours=adv.int("history_hours", 24, 1, 24 * 30),
        price_input=prices.num("input", default_prices[0]),
        price_output=prices.num("output", default_prices[1]),
        price_cache_read=prices.num("cache_read", default_prices[2]),
        price_cache_write=prices.num("cache_write", default_prices[3]),
        data_dir=data_dir,
        log_level=adv.str("log_level", "INFO").upper() or "INFO",
        telegram_api_base=adv.str("telegram_api_base", "https://api.telegram.org").rstrip("/"),
        anthropic_api_base=adv.str("anthropic_api_base", "https://api.anthropic.com").rstrip("/"),
        scheduler_interval_sec=adv.int("scheduler_interval_sec", 30, 1, 3600),
        provider=provider,
        gemini_api_key=gemini_key,
        gemini_model=s.str("gemini_model", "gemini-3.5-flash") or "gemini-3.5-flash",
        gemini_api_base=adv.str("gemini_api_base", "https://generativelanguage.googleapis.com").rstrip("/"),
    )


# ---------------------------------------------------------------- tenant

@dataclass
class Service:
    id: str
    title: str
    duration: int
    price: float
    description: str = ""
    group: str = ""  # розділ у списку послуг, наприклад «👨 Чоловічі»
    icon: str = ""  # смайлик перед назвою у списках послуг і цін (у самих записах назва — без нього)
    short: str = ""  # коротка назва для списків під заголовком розділу («Коротке волосся» замість повної)
    addon_for: list[str] = field(default_factory=list)  # до яких послуг цю можна додати
    # Прихована комбінація «послуга + додаток»: у списках не показується, записатися — лише через «➕ Додати».
    hidden: bool = False
    base_id: str = ""
    addon_id: str = ""

    @property
    def label(self) -> str:
        """Назва для списків: коротка (якщо задана) і зі смайликом (якщо заданий)."""
        name = self.short or self.title
        return f"{self.icon} {name}" if self.icon else name


@dataclass
class Master:
    id: str
    name: str
    services: list[str]
    schedule: dict[int, list[tuple[time, time]]]
    about: str = ""


@dataclass
class Tenant:
    slug: str
    path: Path
    enabled: bool
    name: str
    bot_token: str
    admins: list[int]
    tech_admins: list[int]
    timezone: str
    tz: ZoneInfo
    languages: list[str]
    price_format: str
    info: dict[str, str]
    slot_step_min: int
    days_ahead: int
    min_lead_min: int
    buffer_min: int
    require_phone: bool
    max_active_per_client: int
    cancel_min_hours: int
    holidays: set[date]
    reminder_hours: list[int]
    repeat_enabled: bool
    repeat_after_days: int
    repeat_send_at: time
    notify_new_bookings: bool
    digest_at: time | None
    ai_enabled: bool
    ai_address_form: str
    ai_extra: str
    ai_handoff_hours: int
    ai_max_per_hour: int
    ai_max_per_day: int
    ai_daily_token_limit: int | None
    services: dict[str, Service]
    masters: dict[str, Master]
    texts_override: dict[str, dict[str, str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # ---- час
    def now(self) -> datetime:
        """Поточний місцевий час закладу (без часового поясу, з точністю до хвилини)."""
        return clock.utcnow().astimezone(self.tz).replace(tzinfo=None, second=0, microsecond=0)

    def today(self) -> date:
        return self.now().date()

    # ---- тексти
    @property
    def lang(self) -> str:
        return self.languages[0]

    def lang_for(self, language_code: str | None) -> str:
        code = (language_code or "").lower()[:2]
        return code if code in self.languages else self.languages[0]

    def t(self, lang: str, key: str, **kwargs) -> str:
        lang = lang if lang in SUPPORTED_LANGS else self.lang
        template = (
            self.texts_override.get(lang, {}).get(key)
            or TEXTS[lang].get(key)
            or TEXTS["en"].get(key)
            or key
        )
        return render(template, key, kwargs)

    def all_labels(self, key: str) -> set[str]:
        return {self.t(lang, key) for lang in SUPPORTED_LANGS}

    def price_str(self, price: float | int) -> str:
        try:
            return self.price_format.format(price=fmt_num(price))
        except (KeyError, IndexError, ValueError):
            return fmt_num(price)

    # ---- дати
    def weekday_short(self, d: date, lang: str) -> str:
        return WEEKDAYS_SHORT.get(lang, WEEKDAYS_SHORT["en"])[d.weekday()]

    def day_label(self, d: date, lang: str) -> str:
        """«Сьогодні, сб 24.10» / «Завтра, нд 25.10» / «Пн, 26.10»."""
        today = self.today()
        base = f"{d.day:02d}.{d.month:02d}"
        wd = self.weekday_short(d, lang)
        if d == today:
            return f"{self.t(lang, 'day_today')}, {wd} {base}"
        if d == today + timedelta(days=1):
            return f"{self.t(lang, 'day_tomorrow')}, {wd} {base}"
        return f"{wd[:1].upper()}{wd[1:]}, {base}"

    def day_button(self, d: date, lang: str) -> str:
        today = self.today()
        if d == today:
            return self.t(lang, "day_today")
        if d == today + timedelta(days=1):
            return self.t(lang, "day_tomorrow")
        wd = self.weekday_short(d, lang)
        return f"{wd[:1].upper()}{wd[1:]} {d.day:02d}.{d.month:02d}"

    # ---- графік
    def visible_services(self) -> list[Service]:
        """Послуги для списків (без прихованих комбінацій «послуга + додаток»)."""
        return [s for s in self.services.values() if not s.hidden]

    def service_groups(self) -> list[tuple[str, list[Service]]]:
        """Видимі послуги, на які можна записатися, по розділах (у порядку першої появи в налаштуваннях)."""
        groups: dict[str, list[Service]] = {}
        for s in self.visible_services():
            if self.masters_for(s.id):
                groups.setdefault(s.group, []).append(s)
        return list(groups.items())

    def addons(self) -> list[Service]:
        """Послуги, які можна додати до інших (кнопкою «➕» на картці запису)."""
        return [s for s in self.services.values() if s.addon_for]

    def addons_for(self, service_id: str, master_id: str) -> list[Service]:
        """Комбінації «ця послуга + додаток», які робить цей майстер."""
        master = self.masters.get(master_id)
        return [s for s in self.services.values()
                if s.base_id == service_id and master is not None and s.id in master.services]

    def masters_for(self, service_id: str) -> list[Master]:
        return [m for m in self.masters.values() if service_id in m.services]

    def master_intervals(self, master: Master, d: date) -> list[tuple[datetime, datetime]]:
        if d in self.holidays:
            return []
        return [
            (datetime.combine(d, a), datetime.combine(d, b))
            for a, b in master.schedule.get(d.weekday(), [])
        ]

    def schedule_summary(self, lang: str, master: Master | None = None) -> str:
        """Графік роботи, згрупований за днями: «Пн–Пт: 10:00–19:00»."""
        per_day: list[str] = []
        for wd in range(7):
            if master is not None:
                intervals = master.schedule.get(wd, [])
                text = ", ".join(f"{fmt_hhmm(a)}–{fmt_hhmm(b)}" for a, b in intervals)
            else:
                starts = [iv[0][0] for m in self.masters.values() if m.schedule.get(wd) for iv in [m.schedule[wd]]]
                ends = [iv[-1][1] for m in self.masters.values() if m.schedule.get(wd) for iv in [m.schedule[wd]]]
                text = f"{fmt_hhmm(min(starts))}–{fmt_hhmm(max(ends))}" if starts else ""
            per_day.append(text or self.t(lang, "day_off"))
        names = WEEKDAYS_SHORT.get(lang, WEEKDAYS_SHORT["en"])
        lines, i = [], 0
        while i < 7:
            j = i
            while j + 1 < 7 and per_day[j + 1] == per_day[i]:
                j += 1
            a = names[i][:1].upper() + names[i][1:]
            label = a if i == j else f"{a}–{names[j]}"
            lines.append(f"{label}: {per_day[i]}")
            i = j + 1
        return "\n".join(lines)


def _resolve_secret(value: str) -> str:
    if value.startswith("env:"):
        return os.environ.get(value[4:].strip(), "").strip()
    return value


def load_tenant(path: Path, require_token: bool = True) -> Tenant:
    """require_token=False — для chat/eval у терміналі, де Telegram не потрібен."""
    raw = _read_toml(path)
    slug = path.stem
    if not SLUG_RE.match(slug):
        raise ConfigError(f"{path.name}: назва файлу може містити лише латиницю, цифри, «-» і «_».")
    where = path.name
    s = _Section(raw, where)
    warnings: list[str] = []

    enabled = s.bool("enabled", True)
    name = s.str("name", required=True)

    token = _resolve_secret(s.str("bot_token", required=require_token))
    if not require_token and not TOKEN_RE.match(token):
        token = ""
    elif not TOKEN_RE.match(token):
        raise ConfigError(
            f"{where} → bot_token: це не схоже на токен бота. Отримайте токен у @BotFather "
            f"(виглядає так: 1234567890:AAH...)."
        )

    def ids(key: str) -> list[int]:
        out = []
        for v in s.list(key):
            if isinstance(v, str) and v.strip().lstrip("-").isdigit():
                v = int(v.strip())
            if isinstance(v, bool) or not isinstance(v, int):
                raise ConfigError(f"{where} → {key}: Telegram ID — це число, наприклад [123456789].")
            out.append(v)
        return out

    admins = ids("admins")
    tech_admins = ids("tech_admins")
    if not admins:
        warnings.append("admins порожній — сповіщення про записи й передачу розмов нікому надсилати. "
                        "Напишіть боту /myid і додайте свій ID в admins.")

    tz_name = s.str("timezone", "Europe/Kyiv") or "Europe/Kyiv"
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigError(f"{where} → timezone: невідомий часовий пояс «{tz_name}». "
                          f"Приклади: Europe/Kyiv, Europe/Budapest, Europe/Warsaw.") from None

    langs_raw = s.list("languages", [s.str("language", "uk") or "uk"])
    languages = []
    for lang in langs_raw:
        lang = str(lang).strip().lower()
        if lang not in SUPPORTED_LANGS:
            raise ConfigError(f"{where} → languages: підтримуються {', '.join(SUPPORTED_LANGS)}.")
        if lang not in languages:
            languages.append(lang)
    if not languages:
        languages = ["uk"]

    price_format = s.str("price_format", "{price}") or "{price}"
    if "{price}" not in price_format:
        raise ConfigError(f"{where} → price_format: має містити {{price}}, наприклад \"{{price}} грн\".")

    info_s = s.section("info")
    info = {k: info_s.str(k) for k in ("address", "phone", "maps_url", "directions", "payment", "hours", "extra",
                                       "admin_title")}
    if info["maps_url"] and not info["maps_url"].startswith(("http://", "https://")):
        raise ConfigError(f"{where} → [info] → maps_url: посилання має починатися з https://")

    b = s.section("booking")
    slot_step = b.int("slot_step_min", 30, 5, 240)
    holidays: set[date] = set()
    for h in b.list("holidays"):
        try:
            holidays.add(h if isinstance(h, date) else date.fromisoformat(str(h)))
        except ValueError:
            raise ConfigError(f"{where} → [booking] → holidays: дата «{h}» має бути у форматі \"2026-12-31\".") from None

    r = s.section("reminders")
    reminder_hours = []
    for h in r.list("hours_before", [24, 2]):
        if isinstance(h, bool) or not isinstance(h, int) or not 1 <= h <= 168:
            raise ConfigError(f"{where} → [reminders] → hours_before: цілі числа від 1 до 168, наприклад [24, 2].")
        reminder_hours.append(h)
    reminder_hours = sorted(set(reminder_hours), reverse=True)

    rv = s.section("repeat_visit")
    try:
        repeat_send_at = parse_hhmm(rv.str("send_at", "11:00") or "11:00")
    except ValueError:
        raise ConfigError(f"{where} → [repeat_visit] → send_at: час у форматі \"11:00\".") from None

    n = s.section("notifications")
    digest_raw = n.str("digest_at", "09:00")
    try:
        digest_at = parse_hhmm(digest_raw) if digest_raw else None
    except ValueError:
        raise ConfigError(f"{where} → [notifications] → digest_at: час у форматі \"09:00\" або \"\".") from None

    ai = s.section("ai")
    address_form = ai.str("address_form", "ви").lower() or "ви"
    if address_form not in ("ви", "ти"):
        raise ConfigError(f"{where} → [ai] → address_form: \"ви\" або \"ти\".")
    token_limit = ai.data.get("daily_token_limit")
    if token_limit is not None:
        token_limit = ai.int("daily_token_limit", 0, 0, 10**10)

    # Графік за замовчуванням
    default_schedule = _parse_week(s.section("schedule"), f"{where} → [schedule]")

    # Послуги
    services: dict[str, Service] = {}
    raw_services = raw.get("services") or []
    if not isinstance(raw_services, list) or not raw_services:
        raise ConfigError(f"{where}: додайте хоча б одну послугу в розділі [[services]].")
    for i, item in enumerate(raw_services, 1):
        ss = _Section(item, f"{where} → послуга №{i}")
        sid = ss.str("id", required=True)
        if not ID_RE.match(sid):
            raise ConfigError(f"{ss.where} → id: лише малі латинські літери, цифри, «-», «_», до 16 символів "
                              f"(наприклад \"haircut\").")
        if sid in services:
            raise ConfigError(f"{ss.where} → id: «{sid}» уже використовується іншою послугою.")
        services[sid] = Service(
            id=sid,
            title=ss.str("title", required=True),
            duration=ss.int("duration", 60, 5, 600),
            price=ss.num("price", 0),
            description=ss.str("description"),
            group=ss.str("group"),
            icon=ss.str("icon"),
            short=ss.str("short"),
            addon_for=[str(x) for x in ss.list("addon_for")],
            hidden=ss.bool("addon_only", False),  # лише додатком до іншої послуги, окремо не записують
        )
        if services[sid].hidden and not services[sid].addon_for:
            raise ConfigError(f"{ss.where} → addon_only = true, але не вказано addon_for (до яких послуг додавати).")

    # Майстри
    masters: dict[str, Master] = {}
    raw_masters = raw.get("masters") or []
    if not isinstance(raw_masters, list) or not raw_masters:
        raise ConfigError(f"{where}: додайте хоча б одного майстра в розділі [[masters]].")
    for i, item in enumerate(raw_masters, 1):
        ms = _Section(item, f"{where} → майстер №{i}")
        mid = ms.str("id", required=True)
        if not ID_RE.match(mid) or mid == "any" or mid == "all":
            raise ConfigError(f"{ms.where} → id: лише малі латинські літери, цифри, «-», «_», до 16 символів "
                              f"(наприклад \"andriy\"); слова any/all зарезервовані.")
        if mid in masters:
            raise ConfigError(f"{ms.where} → id: «{mid}» уже використовується іншим майстром.")
        svc_list = ms.list("services", ["*"])
        if "*" in svc_list or "all" in svc_list:
            svc_ids = list(services)
        else:
            svc_ids = []
            for sid in svc_list:
                if sid not in services:
                    raise ConfigError(f"{ms.where} → services: немає послуги з id «{sid}». "
                                      f"Є: {', '.join(services)}.")
                svc_ids.append(sid)
        schedule = dict(default_schedule)
        schedule.update(_parse_week(ms.section("schedule"), f"{ms.where} → schedule", only_given=True))
        if not any(schedule.get(d) for d in range(7)):
            warnings.append(f"У майстра «{ms.str('name') or mid}» немає жодного робочого дня — до нього не запишуться.")
        masters[mid] = Master(id=mid, name=ms.str("name", required=True), services=svc_ids,
                              schedule=schedule, about=ms.str("about"))

    for sid, svc in services.items():
        if not any(sid in m.services for m in masters.values()):
            warnings.append(f"Послугу «{svc.title}» не виконує жоден майстер — на неї неможливо записатися.")

    # Додаткові послуги: для кожної пари «послуга + додаток» — прихована комбінована послуга
    # (сумарні тривалість і ціна). Її роблять ті майстри, що виконують обидві частини.
    for addon in [s for s in services.values() if s.addon_for]:
        for base_id in addon.addon_for:
            base = services.get(base_id)
            if base is None or base_id == addon.id or base.addon_for:
                raise ConfigError(f"{where} → послуга «{addon.id}» → addon_for: «{base_id}» — "
                                  f"має бути id іншої звичайної послуги.")
            doers = [m for m in masters.values() if base_id in m.services and addon.id in m.services]
            if not doers:
                continue
            combo = Service(id=f"{base_id}+{addon.id}", title=f"{base.title} + {addon.title}",
                            duration=base.duration + addon.duration, price=base.price + addon.price,
                            hidden=True, base_id=base_id, addon_id=addon.id)
            services[combo.id] = combo
            for m in doers:
                m.services.append(combo.id)

    texts_override: dict[str, dict[str, str]] = {}
    raw_texts = raw.get("texts") or {}
    if not isinstance(raw_texts, dict):
        raise ConfigError(f"{where} → texts: очікуються розділи [texts.uk], [texts.ru] тощо.")
    for lang, items in raw_texts.items():
        if lang not in SUPPORTED_LANGS or not isinstance(items, dict):
            raise ConfigError(f"{where} → [texts.{lang}]: мова має бути одна з {', '.join(SUPPORTED_LANGS)}.")
        for key, value in items.items():
            if key not in TEXTS["uk"]:
                warnings.append(f"[texts.{lang}] {key}: такого тексту немає, його буде проігноровано.")
            elif not isinstance(value, str):
                raise ConfigError(f"{where} → [texts.{lang}] → {key}: має бути текст у лапках.")
        texts_override[lang] = {k: v for k, v in items.items() if isinstance(v, str)}

    return Tenant(
        slug=slug, path=path, enabled=enabled, name=name, bot_token=token,
        admins=admins, tech_admins=tech_admins, timezone=tz_name, tz=tz,
        languages=languages, price_format=price_format, info=info,
        slot_step_min=slot_step,
        days_ahead=b.int("days_ahead", 14, 1, 90),
        min_lead_min=b.int("min_lead_min", 60, 0, 7 * 24 * 60),
        buffer_min=b.int("buffer_min", 0, 0, 120),
        require_phone=b.bool("require_phone", True),
        max_active_per_client=b.int("max_active_per_client", 2, 1, 20),
        cancel_min_hours=b.int("cancel_min_hours", 0, 0, 168),
        holidays=holidays,
        reminder_hours=reminder_hours,
        repeat_enabled=rv.bool("enabled", True),
        repeat_after_days=rv.int("after_days", 28, 3, 365),
        repeat_send_at=repeat_send_at,
        notify_new_bookings=n.bool("new_bookings", True),
        digest_at=digest_at,
        ai_enabled=ai.bool("enabled", True),
        ai_address_form=address_form,
        ai_extra=ai.str("extra_instructions"),
        ai_handoff_hours=ai.int("handoff_pause_hours", 12, 1, 24 * 7),
        ai_max_per_hour=ai.int("max_messages_per_hour", 20, 1, 1000),
        ai_max_per_day=ai.int("max_messages_per_day", 60, 1, 10000),
        ai_daily_token_limit=token_limit,
        services=services, masters=masters,
        texts_override=texts_override, warnings=warnings,
    )


def _parse_week(sec: _Section, where: str, only_given: bool = False) -> dict[int, list[tuple[time, time]]]:
    out: dict[int, list[tuple[time, time]]] = {}
    for key in sec.data:
        if key not in WEEKDAY_KEYS:
            raise ConfigError(f"{where}: невідомий день «{key}». Використовуйте mon, tue, wed, thu, fri, sat, sun.")
    for wd, key in enumerate(WEEKDAY_KEYS):
        if key in sec.data:
            out[wd] = parse_day_spec(sec.data[key], f"{where} → {key}")
        elif not only_given:
            out[wd] = []
    return out


def load_tenants(tenants_dir: Path, require_token: bool = True) -> tuple[list[Tenant], list[str]]:
    """Повертає (заклади, помилки). Файли з помилками не зупиняють інші заклади."""
    tenants: list[Tenant] = []
    errors: list[str] = []
    if not tenants_dir.exists():
        return [], [f"Не знайдено папку {tenants_dir}"]
    tokens: dict[str, str] = {}
    for path in sorted(tenants_dir.glob("*.toml")):
        if path.name.startswith(("_", ".")):
            continue
        try:
            tenant = load_tenant(path, require_token)
        except ConfigError as e:
            errors.append(str(e))
            continue
        if tenant.enabled and tenant.bot_token and tenant.bot_token in tokens:
            errors.append(f"{path.name}: такий самий bot_token уже використовує {tokens[tenant.bot_token]}. "
                          f"Кожному закладу потрібен свій бот.")
            continue
        if tenant.enabled:
            tokens[tenant.bot_token] = path.name
        tenants.append(tenant)
    return tenants, errors
