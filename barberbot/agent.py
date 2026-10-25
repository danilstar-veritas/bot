"""AI-адміністратор: цикл «модель → інструменти → модель» і історія діалогу.

Модель не може нічого змінити напряму: create_booking / cancel_booking /
reschedule_booking лише перевіряють дані й просять бота показати клієнту
картку з кнопкою підтвердження. Сам запис створює код після натискання.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .booking import BookingError, BookingService
from .config import Settings, Tenant, fmt_hhmm
from .db import DB, parse_dt
from .llm import LLMError
from .prompt import dynamic_prompt, static_prompt, tool_definitions
from .texts import WEEKDAYS_FULL_UK
from .util import clean_ai_text, normalize_phone, parse_date_arg, parse_time_arg, short

log = logging.getLogger("barberbot.agent")

NOTE_PREFIX = "[Системна подія] "


@dataclass
class AgentResult:
    text: str = ""
    effects: list[dict] = field(default_factory=list)
    error: str | None = None
    refusal: bool = False
    tools_used: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ history

def _blocks(content) -> list[dict]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content else []
    return [b for b in content if isinstance(b, dict)]


def strip_thinking(content):
    """Блоки thinking з попередніх ходів не зберігаємо (це дозволено API і економить токени)."""
    if isinstance(content, str):
        return content
    return [b for b in content if b.get("type") not in ("thinking", "redacted_thinking")]


def sanitize_assistant_blocks(content: list[dict]) -> list[dict]:
    """Залишаємо лише відомі поля блоків, щоб безпечно надсилати їх назад."""
    out = []
    for b in content:
        t = b.get("type")
        if t == "text" and b.get("text"):
            out.append({"type": "text", "text": b["text"]})
        elif t == "tool_use":
            out.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b.get("input") or {}})
        elif t in ("thinking", "redacted_thinking"):
            out.append(b)  # усередині поточного циклу thinking-блоки повертаються без змін
    return out


def _has_tool_result(content) -> bool:
    return any(b.get("type") == "tool_result" for b in _blocks(content))


def prepare_history(messages: list[dict]) -> list[dict]:
    """Готує збережену історію: без thinking, починається з репліки клієнта, пари tool_use/tool_result цілі."""
    cleaned: list[dict] = []
    for m in messages:
        content = strip_thinking(m["content"]) if m["role"] == "assistant" else m["content"]
        if not _blocks(content):
            continue
        cleaned.append({"role": m["role"], "content": content})
    # Початок — повідомлення клієнта без tool_result.
    start = 0
    while start < len(cleaned) and (cleaned[start]["role"] != "user" or _has_tool_result(cleaned[start]["content"])):
        start += 1
    cleaned = cleaned[start:]
    # Кожен tool_use має отримати tool_result у наступному повідомленні.
    result: list[dict] = []
    i = 0
    while i < len(cleaned):
        m = cleaned[i]
        if m["role"] == "assistant":
            ids = {b["id"] for b in _blocks(m["content"]) if b.get("type") == "tool_use"}
            if ids:
                nxt = cleaned[i + 1] if i + 1 < len(cleaned) else None
                got = {b.get("tool_use_id") for b in _blocks(nxt["content"])} if nxt and nxt["role"] == "user" else set()
                if not ids <= got:
                    break
        result.append(m)
        i += 1
    return result


def merge_roles(messages: list[dict]) -> list[dict]:
    """API вимагає чергування ролей — зливаємо сусідні повідомлення однієї ролі."""
    merged: list[dict] = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            prev = _blocks(merged[-1]["content"])
            cur = _blocks(m["content"])
            # tool_result-блоки мають іти першими в повідомленні користувача.
            combined = [b for b in prev + cur if b.get("type") == "tool_result"] + \
                       [b for b in prev + cur if b.get("type") != "tool_result"]
            merged[-1] = {"role": m["role"], "content": combined}
        else:
            merged.append({"role": m["role"], "content": m["content"]})
    return merged


def add_note(db: DB, tenant: Tenant, client_id: int, text: str, settings: Settings) -> None:
    """Подія для контексту AI (запис підтверджено, адміністратор відповів тощо)."""
    now = tenant.now()
    if db.has_recent_history(client_id, now - timedelta(hours=settings.history_hours)):
        db.add_history(tenant.slug, client_id, "user", NOTE_PREFIX + text, now)


def history_transcript(db: DB, client_id: int, since: datetime, limit: int = 8) -> list[tuple[str, str]]:
    """Останні репліки (роль, текст) без службових блоків — для сповіщення адміністратору."""
    lines: list[tuple[str, str]] = []
    for m in db.load_history(client_id, since, 60):
        for b in _blocks(m["content"]):
            if b.get("type") == "text" and b.get("text") and not b["text"].startswith(NOTE_PREFIX):
                lines.append((m["role"], b["text"]))
    return lines[-limit:]


# ------------------------------------------------------------------ tools

ERRORS_UK = {
    "no_service": "Немає такої послуги. Використовуй id з переліку послуг.",
    "no_master": "Немає такого майстра. Використовуй id з переліку майстрів або \"any\".",
    "master_no_service": "Цей майстер не виконує цю послугу. Запропонуй іншого майстра або \"any\".",
    "past": "Цей час уже минув.",
    "too_soon": "Записатися можна не пізніше ніж за {minutes} хв до початку. Запропонуй пізніший час.",
    "too_far": "Записатися можна лише на {days} днів уперед.",
    "slot_taken": "Цей час недоступний (зайнятий або поза графіком). Візьми інший час із get_free_slots.",
    "too_many": "У клієнта вже {count} активних записів — це максимум. Запропонуй перенести або скасувати наявний.",
    "week_limit": "На цей тиждень (пн–нд) у клієнта вже {count} записів — це максимум ({limit} на тиждень). "
                  "Запропонуй інший тиждень.",
    "duplicate": "У клієнта вже є запис, що перетинається з цим часом (booking_id {booking_id}).",
    "not_found": "Запис не знайдено серед записів цього клієнта. Виклич get_my_bookings.",
    "inactive": "Цей запис уже неактивний (скасований або минув).",
    "too_late": "До візиту менше {hours} год — онлайн змінити чи скасувати вже не можна. "
                "Порадь клієнту зателефонувати{phone}.",
    "same_time": "Новий час збігається з поточним — нічого змінювати не потрібно.",
    "bad_date": "Неправильна дата. Використовуй формат YYYY-MM-DD.",
    "bad_time": "Неправильний час. Використовуй формат HH:MM.",
    "bad_phone": "Це не схоже на номер телефону. Попроси клієнта написати номер ще раз або натиснути кнопку «Поділитися номером».",
}


class ToolExecutor:
    def __init__(self, tenant: Tenant, booking: BookingService, db: DB, client):
        self.tenant = tenant
        self.booking = booking
        self.db = db
        self.client = client
        self.effects: list[dict] = []

    def _effect(self, effect: dict, unique_type: bool = True) -> None:
        if unique_type:
            self.effects = [e for e in self.effects if e["type"] != effect["type"]]
        self.effects.append(effect)

    def run(self, name: str, args) -> dict:
        args = args if isinstance(args, dict) else {}
        fn = getattr(self, f"tool_{name}", None)
        if fn is None:
            return {"error": "unknown_tool", "message": f"Інструмента {name} немає."}
        try:
            return fn(args)
        except BookingError as e:
            return self._booking_error(e)
        except Exception:
            log.exception("Помилка інструмента %s", name)
            return {"error": "internal", "message": "Внутрішня помилка. Запропонуй клієнту кнопку «📅 Записатися» "
                                                    "або передай питання адміністратору."}

    def _booking_error(self, e: BookingError) -> dict:
        info = dict(e.info)
        phone = self.tenant.info.get("phone")
        info.setdefault("phone", f" за номером {phone}" if phone else "")
        template = ERRORS_UK.get(e.code, "Не вдалося виконати дію.")
        try:
            message = template.format(**info)
        except (KeyError, IndexError):
            message = template
        return {"error": e.code, "message": message}

    # ---- helpers
    def _parse_start(self, args: dict) -> datetime:
        d = parse_date_arg(args.get("date"))
        if d is None:
            raise BookingError("bad_date")
        t = parse_time_arg(args.get("time"))
        if t is None:
            raise BookingError("bad_time")
        return datetime.combine(d, t)

    def _day_info(self, d) -> dict:
        info = {"date": d.isoformat(), "weekday": WEEKDAYS_FULL_UK[d.weekday()]}
        today = self.tenant.today()
        if d == today:
            info["label"] = "сьогодні"
        elif d == today + timedelta(days=1):
            info["label"] = "завтра"
        return info

    def _booking_view(self, b) -> dict:
        start = parse_dt(b["start_at"])
        return {
            "booking_id": b["id"],
            "service": b["service_title"],
            "master": b["master_name"],
            **self._day_info(start.date()),
            "time": fmt_hhmm(start),
            "price": self.tenant.price_str(b["price"]),
        }

    # ---- tools
    def tool_get_free_slots(self, args: dict) -> dict:
        service_id = str(args.get("service_id") or "")
        master_sel = str(args.get("master_id") or "any")
        service = self.booking.service(service_id)
        masters = self.booking.masters_for_sel(service_id, master_sel)
        t_from = parse_time_arg(args.get("time_from"))
        t_to = parse_time_arg(args.get("time_to"))
        lo = fmt_hhmm(t_from) if t_from else None
        hi = fmt_hhmm(t_to) if t_to else None

        def times_for(d, filtered: bool = True) -> dict[str, list[str]]:
            slots = self.booking.free_slots(service_id, master_sel, d)
            if filtered:
                slots = {t: m for t, m in slots.items() if (lo is None or t >= lo) and (hi is None or t <= hi)}
            return slots

        result: dict = {
            "service": {"id": service.id, "title": service.title, "duration_min": service.duration,
                        "price": self.tenant.price_str(service.price)},
            "masters": {m.id: m.name for m in masters},
        }
        date_arg = args.get("date")
        if date_arg:
            d = parse_date_arg(date_arg)
            if d is None:
                raise BookingError("bad_date")
            if d < self.tenant.today():
                raise BookingError("past")
            if d > self.booking.last_day():
                raise BookingError("too_far", days=self.tenant.days_ahead)
            times = times_for(d)
            if times:
                result["days"] = [{**self._day_info(d), "times": times}]
                return result
            result["days"] = []
            all_times = times_for(d, filtered=False)
            if all_times and (lo or hi):
                result["message"] = f"{d.isoformat()} у вказаний проміжок вільного часу немає."
                result["other_times_this_day"] = list(all_times)[:16]
            else:
                result["message"] = f"{d.isoformat()} вільного часу немає (вихідний або все зайнято)."
            nearest = []
            for nd in self.booking.horizon_days():
                if nd <= d:
                    continue
                nt = times_for(nd) or times_for(nd, filtered=False)
                if nt:
                    nearest.append({**self._day_info(nd), "times": nt})
                if len(nearest) >= 2:
                    break
            if nearest:
                result["nearest_days"] = nearest
            return result
        days = []
        for d in self.booking.horizon_days():
            times = times_for(d)
            if times:
                days.append({**self._day_info(d), "times": times})
            if len(days) >= 3:
                break
        result["days"] = days
        if not days:
            result["message"] = f"На найближчі {self.tenant.days_ahead} днів вільного часу немає" + \
                                (" у вказаний проміжок." if (lo or hi) else ".")
        return result

    def tool_create_booking(self, args: dict) -> dict:
        service_id = str(args.get("service_id") or "")
        master_sel = str(args.get("master_id") or "any")
        start = self._parse_start(args)
        master_id = self.booking.validate_new(self.client["id"], service_id, master_sel, start)
        service = self.booking.service(service_id)
        master = self.booking.master(master_id)
        self._effect({"type": "confirm_booking", "service_id": service_id, "master_id": master_id,
                      "start": start})
        return {
            "status": "awaiting_client_confirmation",
            "proposal": {"service": service.title, "master": master.name, **self._day_info(start.date()),
                         "time": fmt_hhmm(start), "duration_min": service.duration,
                         "price": self.tenant.price_str(service.price)},
            "note": "Клієнту показано картку з кнопкою «✅ Підтвердити». Попроси перевірити й натиснути її. "
                    "Запис ще НЕ створено.",
        }

    def tool_get_my_bookings(self, args: dict) -> dict:
        rows = self.booking.upcoming_for_client(self.client["id"])
        if not rows:
            return {"bookings": [], "message": "Активних майбутніх записів немає."}
        return {"bookings": [self._booking_view(b) for b in rows]}

    def _booking_id(self, args: dict) -> int:
        try:
            return int(args.get("booking_id"))
        except (TypeError, ValueError):
            raise BookingError("not_found") from None

    def tool_cancel_booking(self, args: dict) -> dict:
        b = self.booking.validate_cancel(self._booking_id(args), self.client["id"])
        self._effect({"type": "confirm_cancel", "booking_id": b["id"]})
        return {"status": "awaiting_client_confirmation", "booking": self._booking_view(b),
                "note": "Клієнту показано кнопку підтвердження скасування. Запис ще НЕ скасовано."}

    def tool_reschedule_booking(self, args: dict) -> dict:
        start = self._parse_start(args)
        master_sel = args.get("master_id") or None
        b, master_id = self.booking.validate_reschedule(self._booking_id(args), start, master_sel, self.client["id"])
        self._effect({"type": "confirm_reschedule", "booking_id": b["id"], "start": start, "master_id": master_id})
        return {"status": "awaiting_client_confirmation", "booking": self._booking_view(b),
                "new_time": {**self._day_info(start.date()), "time": fmt_hhmm(start),
                             "master": self.booking.master(master_id).name},
                "note": "Клієнту показано кнопку підтвердження перенесення. Запис ще НЕ перенесено."}

    def tool_save_client_contact(self, args: dict) -> dict:
        saved = {}
        name = short(args.get("name") or "", 60).strip()
        phone_raw = str(args.get("phone") or "").strip()
        if phone_raw:
            phone = normalize_phone(phone_raw)
            if phone is None:
                return {"error": "bad_phone", "message": ERRORS_UK["bad_phone"]}
            self.db.set_client_phone(self.client["id"], phone)
            saved["phone"] = phone
        if name:
            self.db.set_client_field(self.client["id"], "name", name)
            saved["name"] = name
        if not saved:
            return {"error": "empty", "message": "Немає що зберігати."}
        return {"ok": True, "saved": saved}

    def tool_handoff_to_owner(self, args: dict) -> dict:
        self._effect({"type": "handoff", "reason": short(args.get("reason") or "", 120),
                      "summary": short(args.get("summary") or "", 500)})
        return {"ok": True, "note": "Адміністратора сповіщено. Коротко скажи клієнту, що адміністратор відповість "
                                    "тут, у цьому чаті. Нічого більше не обіцяй."}


# ------------------------------------------------------------------ agent

class Agent:
    def __init__(self, settings: Settings, llm):
        self.settings = settings
        self.llm = llm

    def build_payload(self, tenant: Tenant, client, messages: list[dict], final_round: bool) -> dict:
        payload = {
            "model": self.settings.model,
            "max_tokens": self.settings.max_tokens,
            "system": [
                {"type": "text", "text": static_prompt(tenant), "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": dynamic_prompt(tenant, client)},
            ],
            "tools": tool_definitions(tenant),
            "messages": merge_roles(messages),
        }
        if self.settings.effort:
            payload["output_config"] = {"effort": self.settings.effort}
        if self.settings.thinking == "disabled":
            payload["thinking"] = {"type": "disabled"}
        if final_round:
            payload["tool_choice"] = {"type": "none"}
        return payload

    async def reply(self, tenant: Tenant, booking: BookingService, db: DB, client, user_text: str) -> AgentResult:
        now = tenant.now()
        history = prepare_history(db.load_history(client["id"], now - timedelta(hours=self.settings.history_hours),
                                                  self.settings.history_messages))
        turn: list[dict] = [{"role": "user", "content": user_text}]
        executor = ToolExecutor(tenant, booking, db, client)
        result = AgentResult()
        stop_reason = None

        for round_no in range(self.settings.max_tool_rounds + 1):
            payload = self.build_payload(tenant, client, history + turn,
                                         final_round=round_no == self.settings.max_tool_rounds)
            try:
                response = await self.llm.create(payload)
            except LLMError as e:
                result.error = str(e)
                result.effects = executor.effects
                return result
            self._log_usage(db, tenant, client["id"], response)
            content = sanitize_assistant_blocks(response.get("content") or [])
            stop_reason = response.get("stop_reason")
            if stop_reason == "refusal":
                result.refusal = True
                return result
            tool_uses = [b for b in content if b["type"] == "tool_use"]
            if stop_reason == "tool_use" and tool_uses:
                turn.append({"role": "assistant", "content": content})
                results = []
                for tu in tool_uses:
                    result.tools_used.append(tu["name"])
                    out = executor.run(tu["name"], tu["input"])
                    block = {"type": "tool_result", "tool_use_id": tu["id"],
                             "content": json.dumps(out, ensure_ascii=False, default=str)}
                    if "error" in out:
                        block["is_error"] = True
                    results.append(block)
                turn.append({"role": "user", "content": results})
                continue
            # Фінальна відповідь (або обрізана max_tokens): незавершені tool_use не зберігаємо.
            final = [b for b in content if b["type"] != "tool_use"]
            if final:
                turn.append({"role": "assistant", "content": final})
            break

        # Текст останньої репліки моделі; якщо вона порожня — останній непорожній текст цього ходу.
        for m in reversed(turn):
            if m["role"] != "assistant":
                continue
            texts = [b["text"] for b in _blocks(m["content"]) if b.get("type") == "text" and b.get("text")]
            if texts:
                result.text = clean_ai_text("\n".join(texts))
                break
        result.effects = executor.effects
        if not result.text and not result.effects and stop_reason == "max_tokens":
            result.error = "Відповідь обрізано (max_tokens)"
        self._save_turn(db, tenant, client["id"], turn, now)
        return result

    def _save_turn(self, db: DB, tenant: Tenant, client_id: int, turn: list[dict], now: datetime) -> None:
        for m in turn:
            content = strip_thinking(m["content"]) if m["role"] == "assistant" else m["content"]
            if _blocks(content):
                db.add_history(tenant.slug, client_id, m["role"], content, now)

    def _log_usage(self, db: DB, tenant: Tenant, client_id: int, response: dict) -> None:
        usage = response.get("usage") or {}
        db.log_event(tenant.slug, client_id, "ai_usage", tenant.now(), {
            "input": usage.get("input_tokens") or 0,
            "output": usage.get("output_tokens") or 0,
            "cache_read": usage.get("cache_read_input_tokens") or 0,
            "cache_write": usage.get("cache_creation_input_tokens") or 0,
            "model": response.get("model") or self.settings.model,
        })
