"""Помічник для персоналу: власник і майстри керують розкладом словами — текстом чи голосом у Telegram
і Messenger, кнопкою «Говорити» в адмінці (PWA), через Siri / Google або зі свого ChatGPT / Claude (MCP).

Один «мозок» для всіх входів:
- StaffUser — хто питає (власник чи майстер) і що йому дозволено;
- StaffOps — розклад, клієнти, звіт і зміни. Кожна зміна двокрокова: propose() перевіряє й описує дію,
  execute() виконує її лише після підтвердження людиною (кнопка, «так» голосом чи текстом);
- StaffAgent — цикл «модель → інструменти → модель» для розмови з персоналом;
- StaffAssistant — вхідна точка для каналів: «так»/«ні» на підготовлену дію або нове питання до AI.
Зміни йдуть через ту саму BookingService і ті самі сповіщення, що й кнопки Telegram-адмінки.

Нова можливість для персоналу = інструмент у staff_tools() (+ _check_/_do_ для змін). Тоді вона одразу
зʼявляється всюди: у помічнику в боті, кнопці «Говорити» в адмінці, Siri і в конекторі ChatGPT / Claude (mcp.py).
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .agent import merge_roles, prepare_history, sanitize_assistant_blocks, strip_thinking
from .booking import BookingError
from .config import Tenant, fmt_hhmm
from .db import dt_str, parse_dt
from .llm import LLMError
from .meta import platform_of
from .stats import compute_stats
from .texts import WEEKDAYS_FULL_UK, Raw
from .util import clean_ai_text, is_affirmative, normalize_phone, parse_date_arg, parse_time_arg, short

log = logging.getLogger("barberbot.staff")

ACTION_TTL = timedelta(minutes=15)
NEGATIVE = {"ні", "нi", "не", "нет", "no", "nope", "nem", "nein", "стоп", "stop", "відміна", "отмена", "не треба",
            "не надо", "не потрібно", "не нужно", "передумав", "передумала"}
# Помилки BookingError → текст для людини (той самий, що бачить і модель).
ERROR_KEYS = {"slot_taken": "slot_taken", "past": "slot_taken", "too_soon": "slot_taken", "too_far": "slot_taken",
              "duplicate": "duplicate", "same_time": "same_time", "not_found": "not_found",
              "inactive": "inactive", "too_late": "inactive", "no_service": "bad_input", "no_master": "bad_input",
              "master_no_service": "bad_input", "bad_date": "bad_input", "bad_time": "bad_input"}


def is_negative(text: str) -> bool:
    cleaned = " ".join(re.sub(r"[!.,?)(:;]+", " ", (text or "").lower()).split())
    return cleaned in NEGATIVE


def strip_tags(text: str) -> str:
    from .app import strip_html  # тут, щоб уникнути циклічного імпорту

    return strip_html(text)


class StaffError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class StaffUser:
    tenant: Tenant
    chat_id: int              # Telegram ID (або чат Messenger), яким людина підключена до закладу
    is_owner: bool
    master_id: str | None     # майстер, яким є ця людина (власник теж може стригти)
    client_id: int            # її рядок у clients — там історія розмови з помічником

    @property
    def role(self) -> str:
        return "owner" if self.is_owner else "master"

    def name(self, db) -> str:
        if self.master_id:
            return self.tenant.masters[self.master_id].name
        client = db.get_client(self.client_id)
        return (client["name"] or client["first_name"] or "") if client else ""


def staff_user(app, tenant: Tenant, chat_id: int) -> StaffUser | None:
    """Власник (є в admins) або підключений майстер; None — це не персонал закладу."""
    is_owner = chat_id in tenant.admins
    master_id = app.master_of(tenant, chat_id)
    if not is_owner and not master_id:
        return None
    client = app.db.get_client_by_tg(tenant.slug, chat_id) \
        or app.db.upsert_client(tenant.slug, chat_id, None, None, None, tenant.lang, tenant.now())
    return StaffUser(tenant, chat_id, is_owner, master_id, client["id"])


@dataclass
class StaffReply:
    text: str = ""                       # відповідь звичайним текстом (і для озвучування)
    action: dict | None = None           # дія чекає підтвердження: {"action_id", "summary", "summary_html"}
    done: bool = False                   # щойно виконано підтверджену дію
    error: str | None = None


# ================================================================ дані й дії

class StaffOps:
    def __init__(self, app):
        self.app = app
        self.db = app.db

    # ---------------------------------------------------------- допоміжне
    def _t(self, u: StaffUser, key: str, **kw) -> str:
        return u.tenant.t(u.tenant.lang, key, **kw)

    def _err(self, u: StaffUser, code: str) -> StaffError:
        return StaffError(code, strip_tags(self._t(u, f"staff_err_{code}")))

    def _booking_err(self, u: StaffUser, e: BookingError) -> StaffError:
        return self._err(u, ERROR_KEYS.get(e.code, "other"))

    def _booking(self, u: StaffUser):
        return self.app.bookings[u.tenant.slug]

    def _day(self, u: StaffUser, value, past_days: int = 0) -> date:
        d = parse_date_arg(value) if value else u.tenant.today()
        today = u.tenant.today()
        if d is None or not today - timedelta(days=past_days) <= d <= today + timedelta(days=90):
            raise self._err(u, "bad_input")
        return d

    def _time(self, u: StaffUser, value) -> time:
        t = parse_time_arg(value)
        if t is None:
            raise self._err(u, "bad_input")
        return t

    def _scope(self, u: StaffUser, master_id: str | None) -> list[str]:
        """Майстри, чий розклад бачить людина: майстер — лише свій."""
        tenant = u.tenant
        if not u.is_owner:
            return [u.master_id]
        if master_id and master_id not in ("any", "all", "*"):
            if master_id not in tenant.masters:
                raise self._err(u, "bad_input")
            return [master_id]
        return list(tenant.masters)

    def _own_master(self, u: StaffUser, master_id: str | None) -> str | None:
        """Майстер для дії: майстер діє лише за себе; власник — за вказаного (None — не вказано)."""
        if not u.is_owner:
            if master_id and master_id not in ("any", u.master_id):
                raise self._err(u, "not_yours")
            return u.master_id
        if master_id in (None, "", "any"):
            return None
        if master_id not in u.tenant.masters:
            raise self._err(u, "bad_input")
        return master_id

    def client_name(self, u: StaffUser, client) -> str:
        if client is None:
            return self._t(u, "adm_client_noname")
        return client["name"] or " ".join(p for p in (client["first_name"], client["last_name"]) if p) \
            or self._t(u, "adm_client_noname")

    def booking_view(self, u: StaffUser, b) -> dict:
        tenant = u.tenant
        start = parse_dt(b["start_at"])
        client = self.db.get_client(b["client_id"])
        return {
            "booking_id": b["id"], "date": start.date().isoformat(), "day": tenant.day_label(start.date(), tenant.lang),
            "time": fmt_hhmm(start), "end": b["end_at"][11:16], "master_id": b["master_id"],
            "master": b["master_name"], "service_id": b["service_id"], "service": b["service_title"],
            "client_id": b["client_id"], "client": self.client_name(u, client),
            "phone": (client["phone"] or "") if client else "", "in_chat": bool(client and client["tg_id"] > 0),
            "price": tenant.price_str(b["price"]), "status": b["status"], "note": b["note"] or "",
            "source": b["source"], "confirmed": bool(b["client_confirmed"]), "prepay": b["prepay"] or "",
            "past": start <= tenant.now(),
        }

    def block_view(self, u: StaffUser, bl) -> dict:
        tenant = u.tenant
        start, end = parse_dt(bl["start_at"]), parse_dt(bl["end_at"])
        whole = start.time() == time.min and end - start >= timedelta(days=1)
        master = tenant.masters[bl["master_id"]].name if bl["master_id"] in tenant.masters \
            else self._t(u, "adm_all_masters")
        own = u.is_owner or (bl["master_id"] == u.master_id and bl["created_by"] == "master")
        return {"block_id": bl["id"], "master_id": bl["master_id"], "master": master,
                "date": start.date().isoformat(), "day": tenant.day_label(start.date(), tenant.lang),
                "from": "" if whole else fmt_hhmm(start), "to": "" if whole else fmt_hhmm(end),
                "range": self._t(u, "adm_whole_day") if whole else f"{fmt_hhmm(start)}–{fmt_hhmm(end)}",
                "whole_day": whole, "note": bl["note"] or "", "can_open": own}

    # ---------------------------------------------------------- читання
    def schedule(self, u: StaffUser, day=None, days: int = 1, master_id: str | None = None) -> dict:
        tenant = u.tenant
        first = self._day(u, day, past_days=31)
        days = max(1, min(int(days or 1), 14))
        scope = self._scope(u, master_id)
        result = []
        for i in range(days):
            d = first + timedelta(days=i)
            start = datetime.combine(d, time.min)
            rows = [r for r in self._booking(u).day_bookings(d) if r["master_id"] in scope]
            blocks = [bl for bl in self.db.q("SELECT * FROM blocks WHERE tenant = ? AND start_at < ? AND end_at > ? "
                                             "ORDER BY start_at", tenant.slug, dt_str(start + timedelta(days=1)),
                                             dt_str(start))
                      if bl["master_id"] is None or bl["master_id"] in scope]
            hours = {}
            for mid in scope:
                intervals = tenant.master_intervals(tenant.masters[mid], d)
                hours[mid] = f"{fmt_hhmm(intervals[0][0])}–{fmt_hhmm(intervals[-1][1])}" if intervals else ""
            result.append({"date": d.isoformat(), "day": tenant.day_label(d, tenant.lang),
                           "weekday": WEEKDAYS_FULL_UK[d.weekday()],
                           "bookings": [self.booking_view(u, r) for r in rows],
                           "blocks": [self.block_view(u, bl) for bl in blocks],
                           "hours": {tenant.masters[m].name: h or "off" for m, h in hours.items()}})
        return {"days": result}

    def free_slots(self, u: StaffUser, service_id: str, day=None, master_id: str | None = None) -> dict:
        tenant = u.tenant
        d = self._day(u, day)
        master = self._own_master(u, master_id) or "any"
        try:
            slots = self._booking(u).free_slots(service_id, master, d, admin=True)
        except BookingError as e:
            raise self._booking_err(u, e) from None
        return {"date": d.isoformat(), "day": tenant.day_label(d, tenant.lang), "service_id": service_id,
                "times": {t: [tenant.masters[m].name for m in ms] for t, ms in slots.items()}}

    def find_clients(self, u: StaffUser, query: str) -> dict:
        tenant = u.tenant
        found = []
        for c in self.db.search_clients(tenant.slug, short(query or "", 60), limit=8):
            if c["tg_id"] == u.chat_id:
                continue
            upcoming = [self.booking_view(u, b) for b in self.db.client_upcoming(c["id"], tenant.now())]
            if not u.is_owner:
                upcoming = [b for b in upcoming if b["master_id"] == u.master_id]
            found.append({"client_id": c["id"], "name": self.client_name(u, c), "phone": c["phone"] or "",
                          "in_chat": c["tg_id"] > 0, "upcoming": upcoming})
        return {"clients": found}

    def blocks(self, u: StaffUser) -> dict:
        rows = [bl for bl in self.db.future_blocks(u.tenant.slug, u.tenant.now())
                if u.is_owner or bl["master_id"] in (u.master_id, None)]
        return {"blocks": [self.block_view(u, bl) for bl in rows[:60]]}

    def report(self, u: StaffUser, period: str = "today", days: int | None = None) -> dict:
        """Підсумки за період; days — довільна кількість останніх днів (разом із сьогоднішнім)."""
        tenant = u.tenant
        today = tenant.today()
        spans = {"today": (today, 1), "yesterday": (today - timedelta(days=1), 1), "tomorrow": (today + timedelta(days=1), 1),
                 "week": (today - timedelta(days=6), 7), "month": (today - timedelta(days=29), 30)}
        if days:
            days = max(1, min(self._int(u, days), 3650))
            period = "custom"
            spans[period] = (today - timedelta(days=days - 1), days)
        if period not in spans:
            period = "today"
        first, days = spans[period]
        start = datetime.combine(first, time.min)
        scope = self._scope(u, None)
        rows = [r for r in self.db.bookings_between(tenant.slug, start, start + timedelta(days=days),
                                                    ("active", "no_show", "cancelled")) if r["master_id"] in scope]
        now = tenant.now()
        done = [r for r in rows if r["status"] == "active" and parse_dt(r["end_at"]) <= now]
        planned = [r for r in rows if r["status"] == "active" and parse_dt(r["end_at"]) > now]
        per: dict[str, dict] = {}
        for r in done:
            item = per.setdefault(r["master_name"], {"visits": 0, "revenue": 0.0})
            item["visits"] += 1
            item["revenue"] += r["price"] or 0
        result = {
            "period": period, "from": first.isoformat(), "to": (first + timedelta(days=days - 1)).isoformat(),
            "visits_done": len(done), "revenue": tenant.price_str(round(sum(r["price"] or 0 for r in done))),
            "still_planned": len(planned), "expected": tenant.price_str(round(sum(r["price"] or 0 for r in planned))),
            "no_shows": sum(1 for r in rows if r["status"] == "no_show"),
            "cancelled": sum(1 for r in rows if r["status"] == "cancelled"),
            "by_master": [{"master": name, "visits": v["visits"], "revenue": tenant.price_str(round(v["revenue"]))}
                          for name, v in sorted(per.items(), key=lambda kv: -kv[1]["revenue"])],
        }
        if u.is_owner and days >= 7:
            s = compute_stats(self.db, tenant, self.app.settings, days=days)
            result["bot"] = {"bookings_created": s["created"], "by_ai": s["by_ai"], "by_buttons": s["by_buttons"],
                             "at_night": s["night"], "handled_without_human": s["auto_rate"],
                             "ai_cost_usd": s["cost"]}
        return result

    def shop(self, u: StaffUser) -> dict:
        """Стан закладу для власника: AI для клієнтів, ціни (змінені й з файлу), хто з майстрів підключений."""
        if not u.is_owner:
            raise self._err(u, "owner_only")
        tenant, app = u.tenant, self.app
        links = app.master_links(tenant)
        masters = []
        for m in tenant.masters.values():
            client = self.db.get_client_by_tg(tenant.slug, links[m.id]) if m.id in links else None
            masters.append({"master_id": m.id, "name": m.name, "connected": m.id in links,
                            "connected_as": app.client_label(tenant, client) if client else "",
                            "schedule": tenant.schedule_summary(tenant.lang, m)})
        return {"shop": tenant.name, "client_ai": app.ai_status(tenant),
                "services": [{"service_id": s.id, "title": s.title, "minutes": s.duration,
                              "price": tenant.price_str(s.price),
                              # у комбінацій «послуга + додаток» ціни з файлу немає — вона рахується з частин
                              "price_in_settings_file": tenant.price_str(s.config_price)
                              if s.config_price is not None else None,
                              "editable": not s.base_id}
                             for s in tenant.services.values() if not (s.hidden and not s.base_id)],
                "masters": masters}

    def chats(self, u: StaffUser, hours: int = 72) -> dict:
        """Розмови з клієнтами за останні дні: хто писав, що писав, чи AI зараз на паузі (чекають людину)."""
        if not u.is_owner:
            raise self._err(u, "owner_only")
        tenant = u.tenant
        now = tenant.now()
        since = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        rows = self.db.q("""SELECT e.client_id, e.kind, e.data, e.created_at FROM events e
                            WHERE e.tenant = ? AND e.kind IN ('msg_in', 'msg_out', 'admin_reply') AND e.created_at >= ?
                              AND e.client_id IS NOT NULL ORDER BY e.id""", tenant.slug, since)
        staff = set(tenant.admins) | set(self.app.master_links(tenant).values())
        by_client: dict[int, list] = {}
        for r in rows:
            data = json.loads(r["data"] or "{}")
            by_client.setdefault(r["client_id"], []).append(
                {"from": {"msg_in": "client", "msg_out": "bot", "admin_reply": "admin"}[r["kind"]],
                 "text": data.get("text") or "", "at": r["created_at"][:16]})
        result = []
        for client_id, messages in by_client.items():
            client = self.db.get_client(client_id)
            if client is None or client["tg_id"] in staff:
                continue
            paused = bool(client["paused_until"]) and parse_dt(client["paused_until"]) > now
            result.append({"client_id": client_id, "name": self.client_name(u, client), "phone": client["phone"] or "",
                           "channel": platform_of(client["tg_id"]) or ("telegram" if client["tg_id"] > 0 else ""),
                           "waiting_for_human": paused, "last_at": messages[-1]["at"], "messages": messages[-12:]})
        result.sort(key=lambda c: c["last_at"], reverse=True)
        result.sort(key=lambda c: not c["waiting_for_human"])  # спершу ті, хто чекає на людину
        return {"chats": result[:30]}

    # ---------------------------------------------------------- зміни: перевірка й опис
    def _range_text(self, u: StaffUser, start: datetime, end: datetime) -> str:
        if start.time() == time.min and end - start >= timedelta(days=1):
            return self._t(u, "adm_whole_day")
        return f"{fmt_hhmm(start)}–{fmt_hhmm(end)}"

    def _conflicts(self, u: StaffUser, start: datetime, end: datetime, master_id: str | None) -> str:
        rows = self.db.active_bookings_overlapping(u.tenant.slug, start, end, master_id)
        if not rows:
            return ""
        lines = "".join(f"\n• {b['start_at'][11:16]} {b['master_name']} · "
                        f"{self.client_name(u, self.db.get_client(b['client_id']))}" for b in rows)
        return self._t(u, "staff_sum_conflicts", lines=lines)

    def _check_block(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        tenant = u.tenant
        master_id = a.get("master_id")
        # Повторна перевірка вже перевірених даних (a["start"]): master_id None там означає «усім майстрам».
        if u.is_owner and (master_id in ("all", "*") or (master_id is None and a.get("start"))):
            master_id = None
        else:
            master_id = self._own_master(u, master_id) or u.master_id
            if master_id is None:
                raise self._err(u, "bad_input")  # власник не сказав, чий час закрити
        if a.get("start"):  # уже перевірені дані (повторна перевірка перед виконанням)
            start, end = parse_dt(a["start"]), parse_dt(a["end"])
        else:
            d = self._day(u, a.get("date"))
            if a.get("time_from") or a.get("time_to"):
                start = datetime.combine(d, self._time(u, a.get("time_from")))
                end = datetime.combine(d, self._time(u, a.get("time_to") or "23:59"))
            else:
                start = datetime.combine(d, time.min)
                end = start + timedelta(days=1)
        if end <= start or end <= tenant.now():
            raise self._err(u, "bad_input")
        note = short(a.get("note") or "", 100)
        name = tenant.masters[master_id].name if master_id else self._t(u, "adm_all_masters")
        summary = self._t(u, "staff_sum_block", master=name, day=tenant.day_label(start.date(), tenant.lang),
                          range=self._range_text(u, start, end), note=f" — {note}" if note else "")
        summary += self._conflicts(u, start, end, master_id)
        return {"master_id": master_id, "start": dt_str(start), "end": dt_str(end), "note": note}, summary

    def _check_unblock(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        bl = self.db.get_block(u.tenant.slug, self._int(u, a.get("block_id")))
        if bl is None or parse_dt(bl["end_at"]) <= u.tenant.now():
            raise self._err(u, "not_found")
        if not u.is_owner and (bl["master_id"] != u.master_id or bl["created_by"] != "master"):
            raise self._err(u, "not_yours")
        view = self.block_view(u, bl)
        return {"block_id": bl["id"]}, self._t(u, "staff_sum_unblock", master=view["master"], day=view["day"],
                                               range=view["range"])

    def _int(self, u: StaffUser, value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise self._err(u, "not_found") from None

    def _own_booking(self, u: StaffUser, booking_id):
        b = self.db.get_booking(self._int(u, booking_id))
        if b is None or b["tenant"] != u.tenant.slug:
            raise self._err(u, "not_found")
        if not u.is_owner and b["master_id"] != u.master_id:
            raise self._err(u, "not_yours")
        return b

    def _summary(self, u: StaffUser, b) -> Raw:
        return Raw(self.app._booking_summary(u.tenant, b, self.db.get_client(b["client_id"])))

    def _check_no_show(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        b = self._own_booking(u, a.get("booking_id"))
        if b["status"] != "active" or parse_dt(b["start_at"]).date() > u.tenant.today():
            raise self._err(u, "inactive")
        return {"booking_id": b["id"]}, self._t(u, "staff_sum_noshow", booking=self._summary(u, b))

    def _check_book(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        tenant, db = u.tenant, self.db
        service_id = str(a.get("service_id") or "")
        service = tenant.services.get(service_id)
        if service is None:
            raise self._err(u, "bad_input")
        master_sel = self._own_master(u, a.get("master_id")) or "any"
        if a.get("start"):
            start = parse_dt(a["start"])
        else:
            start = datetime.combine(self._day(u, a.get("date")), self._time(u, a.get("time")))
        client = None
        if a.get("client_id"):
            client = db.get_client(self._int(u, a["client_id"]))
            if client is None or client["tenant"] != tenant.slug:
                raise self._err(u, "not_found")
        name = short(str(a.get("client_name") or "").strip(), 60)
        phone_raw = str(a.get("client_phone") or "").strip()
        phone = normalize_phone(phone_raw) if phone_raw else None
        if phone_raw and not phone:
            raise self._err(u, "bad_input")
        if client is None and phone:
            client = db.find_client_by_phone(tenant.slug, phone)
        if client is None and len(name) < 2:
            raise self._err(u, "no_client")
        try:
            master_id = self._booking(u).validate_new(client["id"] if client else 0, service_id, master_sel, start,
                                                      admin=True)
        except BookingError as e:
            raise self._booking_err(u, e) from None
        label = self.client_name(u, client) if client else name
        if phone or (client and client["phone"]):
            label += f" · {phone or client['phone']}"
        note = short(str(a.get("note") or ""), 300)
        summary = self._t(u, "staff_sum_book", client=label, service=service.title,
                          master=tenant.masters[master_id].name, day=tenant.day_label(start.date(), tenant.lang),
                          time=fmt_hhmm(start), price=tenant.price_str(service.price),
                          note=f"\n📝 {note}" if note else "")
        return {"service_id": service_id, "master_id": master_id, "start": dt_str(start),
                "client_id": client["id"] if client else None, "client_name": name, "client_phone": phone,
                "note": note}, summary

    def _check_reschedule(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        if not u.is_owner:
            raise self._err(u, "owner_only")
        tenant = u.tenant
        b = self._own_booking(u, a.get("booking_id"))
        if a.get("start"):
            start = parse_dt(a["start"])
        else:
            start = datetime.combine(self._day(u, a.get("date")), self._time(u, a.get("time")))
        master_sel = a.get("master_id") or None
        if master_sel and master_sel not in tenant.masters:
            raise self._err(u, "bad_input")
        try:
            b, master_id = self._booking(u).validate_reschedule(b["id"], start, master_sel, None, admin=True)
        except BookingError as e:
            raise self._booking_err(u, e) from None
        new = f"{tenant.day_label(start.date(), tenant.lang)}, {fmt_hhmm(start)} · {tenant.masters[master_id].name}"
        return {"booking_id": b["id"], "start": dt_str(start), "master_id": master_id}, \
            self._t(u, "staff_sum_resched", booking=self._summary(u, b), new=new)

    def _check_cancel(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        if not u.is_owner:
            raise self._err(u, "owner_only")
        b = self._own_booking(u, a.get("booking_id"))
        try:
            self._booking(u).validate_cancel(b["id"], None)
        except BookingError as e:
            raise self._booking_err(u, e) from None
        return {"booking_id": b["id"]}, self._t(u, "staff_sum_cancel", booking=self._summary(u, b))

    def _check_message(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        if not u.is_owner:
            raise self._err(u, "owner_only")
        client = self.db.get_client(self._int(u, a.get("client_id")))
        if client is None or client["tenant"] != u.tenant.slug:
            raise self._err(u, "not_found")
        if client["tg_id"] <= 0 or client["blocked"]:
            raise self._err(u, "no_chat")
        text = str(a.get("text") or "").strip()[:1000]
        if not text:
            raise self._err(u, "bad_input")
        return {"client_id": client["id"], "text": text}, \
            self._t(u, "staff_sum_message", client=self.client_name(u, client), text=text)

    def _owner(self, u: StaffUser) -> None:
        if not u.is_owner:
            raise self._err(u, "owner_only")

    def _check_price(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        self._owner(u)
        tenant = u.tenant
        s = tenant.services.get(str(a.get("service_id") or ""))
        if s is None or s.base_id:
            raise self._err(u, "bad_input")
        if a.get("price") in (None, ""):
            price = None  # повернути ціну з файлу налаштувань
        else:
            try:
                price = round(float(str(a["price"]).replace(",", ".")), 2)
            except ValueError:
                raise self._err(u, "bad_input") from None
            if not 0 <= price <= 1_000_000:
                raise self._err(u, "bad_input")
        new = s.config_price if price is None else price
        if new == s.price:
            raise self._err(u, "same_price")
        return {"service_id": s.id, "price": price}, \
            self._t(u, "staff_sum_price", title=s.title, old=tenant.price_str(s.price), new=tenant.price_str(new))

    def _check_client_ai(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        self._owner(u)
        on = bool(a.get("on"))
        return {"on": on}, self._t(u, "staff_sum_ai_on" if on else "staff_sum_ai_off")

    def _check_resume_client(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        self._owner(u)
        client = self.db.get_client(self._int(u, a.get("client_id")))
        if client is None or client["tenant"] != u.tenant.slug:
            raise self._err(u, "not_found")
        return {"client_id": client["id"]}, self._t(u, "staff_sum_resume_client", client=self.client_name(u, client))

    def _check_invite(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        from .masters import INVITE_HOURS

        self._owner(u)
        master = u.tenant.masters.get(str(a.get("master_id") or ""))
        if master is None:
            raise self._err(u, "bad_input")
        return {"master_id": master.id}, self._t(u, "staff_sum_invite", name=master.name, hours=INVITE_HOURS)

    def _check_export(self, u: StaffUser, a: dict) -> tuple[dict, str]:
        self._owner(u)
        if platform_of(u.chat_id) or u.chat_id <= 0:
            raise self._err(u, "no_telegram")
        days = max(1, min(self._int(u, a.get("days") or 30), 3650))
        return {"days": days}, self._t(u, "staff_sum_export", days=days)

    KINDS = ("block", "unblock", "no_show", "book", "reschedule", "cancel", "message",
             "price", "client_ai", "resume_client", "invite", "export")

    def propose(self, u: StaffUser, kind: str, args: dict) -> dict:
        """Перевірити дію й відкласти її до підтвердження. Помилка — StaffError з поясненням."""
        if kind not in self.KINDS:
            raise self._err(u, "bad_input")
        plan, summary = getattr(self, f"_check_{kind}")(u, args if isinstance(args, dict) else {})
        action_id = secrets.token_hex(4)
        until = u.tenant.now() + ACTION_TTL
        self.db.kv_set(u.tenant.slug, f"staff_action:{action_id}",
                       json.dumps({"chat": u.chat_id, "kind": kind, "args": plan, "summary": summary,
                                   "until": until.isoformat()}, ensure_ascii=False))
        self.db.kv_set(u.tenant.slug, f"staff_pending:{u.chat_id}", action_id)
        return {"action_id": action_id, "kind": kind, "summary": strip_tags(summary), "summary_html": summary}

    def _load(self, u: StaffUser, action_id: str) -> dict | None:
        raw = self.db.kv_get(u.tenant.slug, f"staff_action:{action_id}") if action_id else None
        try:
            item = json.loads(raw) if raw else None
        except ValueError:
            item = None
        if not item or item.get("chat") != u.chat_id or datetime.fromisoformat(item["until"]) < u.tenant.now():
            return None
        return item

    def pending(self, u: StaffUser) -> str | None:
        """Дія, яка чекає «так» від цієї людини."""
        action_id = self.db.kv_get(u.tenant.slug, f"staff_pending:{u.chat_id}")
        return action_id if action_id and self._load(u, action_id) else None

    def pending_view(self, u: StaffUser) -> dict | None:
        action_id = self.pending(u)
        if not action_id:
            return None
        item = self._load(u, action_id)
        return {"action_id": action_id, "kind": item["kind"], "summary": strip_tags(item["summary"]),
                "summary_html": item["summary"]}

    def drop(self, u: StaffUser, action_id: str | None = None) -> None:
        action_id = action_id or self.db.kv_get(u.tenant.slug, f"staff_pending:{u.chat_id}")
        if action_id:
            self.db.kv_delete(u.tenant.slug, f"staff_action:{action_id}")
        if self.db.kv_get(u.tenant.slug, f"staff_pending:{u.chat_id}") == action_id:
            self.db.kv_delete(u.tenant.slug, f"staff_pending:{u.chat_id}")

    # ---------------------------------------------------------- зміни: виконання
    async def execute(self, u: StaffUser, action_id: str) -> dict:
        """Виконати підтверджену дію. {"ok", "text", "html"}; застаріла чи чужа дія — StaffError."""
        item = self._load(u, action_id)
        if item is None:
            raise self._err(u, "expired")
        self.drop(u, action_id)
        plan, summary = getattr(self, f"_check_{item['kind']}")(u, item["args"])  # стан міг змінитися
        html = await getattr(self, f"_do_{item['kind']}")(u, plan)
        self.db.log_event(u.tenant.slug, u.client_id, "staff_action", u.tenant.now(),
                          {"kind": item["kind"], "args": plan})
        return {"ok": True, "text": strip_tags(html), "html": html, "summary": strip_tags(summary)}

    def _done(self, u: StaffUser, notified: bool | None, client=None) -> str:
        if notified is None:
            return self._t(u, "staff_done")
        if notified:
            return self._t(u, "staff_done_client")
        phone = client["phone"] if client is not None and client["phone"] else ""
        return self._t(u, "staff_done_no_client", phone=f" ({phone})" if phone else "")

    async def _do_block(self, u: StaffUser, p: dict) -> str:
        tenant = u.tenant
        start, end = parse_dt(p["start"]), parse_dt(p["end"])
        master_id = p["master_id"]
        note = p["note"] or (tenant.masters[master_id].name if master_id and not u.is_owner else "")
        _, conflicts = self._booking(u).add_block(master_id, start, end, note,
                                                  created_by=None if u.is_owner else "master")
        if not u.is_owner:
            app = self.app
            rng = self._range_text(u, start, end)
            text = self._t(u, "adm_master_off", master=tenant.masters[master_id].name,
                           day=tenant.day_label(start.date(), tenant.lang), range=rng)
            if conflicts:
                text += self._t(u, "adm_master_off_conflicts", lines=app._conflict_lines(tenant, conflicts))
            await app.notify_admins(tenant, text)
        return self._done(u, None)

    async def _do_unblock(self, u: StaffUser, p: dict) -> str:
        tenant = u.tenant
        bl = self.db.get_block(tenant.slug, p["block_id"])
        view = self.block_view(u, bl)
        self.db.delete_block(tenant.slug, bl["id"])
        if not u.is_owner:
            await self.app.notify_admins(tenant, self._t(u, "adm_master_on", master=view["master"], day=view["day"],
                                                         range=view["range"]))
        return self._done(u, None)

    async def _do_no_show(self, u: StaffUser, p: dict) -> str:
        tenant = u.tenant
        b = self._booking(u).mark_no_show(p["booking_id"])
        if not u.is_owner:
            from .telegram import ibtn, inline_kb

            await self.app.notify_admins(tenant, self._t(
                u, "adm_master_noshow", master=tenant.masters[u.master_id].name, booking=self._summary(u, b)),
                inline_kb([[ibtn(self._t(u, "btn_adm_open"), f"aK:{b['id']}")]]))
        return self._done(u, None)

    async def _do_book(self, u: StaffUser, p: dict) -> str:
        tenant, db, app = u.tenant, self.db, self.app
        start = parse_dt(p["start"])
        client = db.get_client(p["client_id"]) if p["client_id"] else None
        if client is None:
            client = db.create_offline_client(tenant.slug, p["client_name"], p["client_phone"], tenant.now())
        if not client["name"] and p["client_name"]:
            db.set_client_field(client["id"], "name", p["client_name"])
        if p["client_phone"] and not client["phone"]:
            db.set_client_phone(client["id"], p["client_phone"])
        try:
            b = self._booking(u).create(client["id"], p["service_id"], p["master_id"], start, "admin")
        except BookingError as e:
            raise self._booking_err(u, e) from None
        if p["note"]:
            db.set_booking_field(b["id"], "note", p["note"])
        client = db.get_client(client["id"])
        notified = await app.tell_client_booked(tenant, b)
        if tenant.notify_new_bookings:
            text = self._t(u, "adm_new_booking", via=self._t(u, "adm_via_admin"),
                           client=app.client_label(tenant, client), service=b["service_title"],
                           master=b["master_name"], day=tenant.day_label(start.date(), tenant.lang),
                           time=fmt_hhmm(start), price=tenant.price_str(b["price"]))
            for admin in tenant.admins:
                if admin != u.chat_id:
                    await app.send(tenant, admin, text)
        if b["master_id"] != u.master_id:
            await app.notify_master(tenant, b, "mst_new")
        return self._done(u, notified, client)

    async def _do_reschedule(self, u: StaffUser, p: dict) -> str:
        tenant = u.tenant
        try:
            old, new = self._booking(u).reschedule(p["booking_id"], parse_dt(p["start"]), p["master_id"], None,
                                                   admin=True)
        except BookingError as e:
            raise self._booking_err(u, e) from None
        await self.app.notify_master_resched(tenant, old, new)
        notified = await self.app.tell_client_rescheduled(tenant, old, new)
        return self._done(u, notified, self.db.get_client(new["client_id"]))

    async def _do_cancel(self, u: StaffUser, p: dict) -> str:
        tenant = u.tenant
        try:
            b = self._booking(u).cancel(p["booking_id"], "admin")
        except BookingError as e:
            raise self._booking_err(u, e) from None
        await self.app.notify_master(tenant, b, "mst_cancelled")
        notified = await self.app.tell_client_cancelled(tenant, b)
        return self._done(u, notified, self.db.get_client(b["client_id"]))

    async def _do_message(self, u: StaffUser, p: dict) -> str:
        from .agent import add_note

        tenant, db = u.tenant, self.db
        client = db.get_client(p["client_id"])
        lang = client["lang"] or tenant.lang
        title = tenant.info_in("admin_title", lang) or tenant.t(lang, "admin_title")
        sent = await self.app.send(tenant, client["tg_id"],
                                   tenant.t(lang, "admin_reply_to_client", title=title, text=p["text"]), tag="human")
        if sent is None:
            raise self._err(u, "no_chat")
        now = tenant.now()
        db.set_client_field(client["id"], "paused_until", dt_str(now + timedelta(hours=tenant.ai_handoff_hours)))
        add_note(db, tenant, client["id"], f"Адміністратор написав клієнту: «{short(p['text'], 300)}».",
                 self.app.settings)
        db.log_event(tenant.slug, client["id"], "admin_reply", now, {"text": short(p["text"], 2000)})
        return self._done(u, True)

    async def _do_price(self, u: StaffUser, p: dict) -> str:
        tenant, app = u.tenant, self.app
        s = tenant.services[p["service_id"]]
        old = s.price
        if p["price"] is None or p["price"] == s.config_price:
            self.db.kv_delete(tenant.slug, f"price:{s.id}")
        else:
            self.db.kv_set(tenant.slug, f"price:{s.id}", f"{p['price']:g}")
        app.apply_prices(tenant)
        text = self._t(u, "adm_price_done", title=s.title, old=tenant.price_str(old), new=tenant.price_str(s.price))
        if any(c.base_id == s.id or c.addon_id == s.id for c in tenant.services.values()):
            text += self._t(u, "adm_price_combos")
        note = self._t(u, "adm_price_changed_note", admin=app.client_label(tenant, self.db.get_client(u.client_id)),
                       title=s.title, old=tenant.price_str(old), new=tenant.price_str(s.price))
        for admin in tenant.admins:
            if admin != u.chat_id:
                await app.send(tenant, admin, note)
        return text

    async def _do_client_ai(self, u: StaffUser, p: dict) -> str:
        self.db.kv_set(u.tenant.slug, "paused", "0" if p["on"] else "1")
        return self._t(u, "adm_resumed_all" if p["on"] else "adm_paused")

    async def _do_resume_client(self, u: StaffUser, p: dict) -> str:
        self.resume_ai(u, p["client_id"])
        return self._done(u, None)

    async def _do_invite(self, u: StaffUser, p: dict) -> str:
        from .masters import INVITE_HOURS

        tenant = u.tenant
        link = await self.app.master_invite_link(tenant, p["master_id"])
        if not link:
            raise StaffError("no_username", strip_tags(self._t(u, "adm_master_no_username")))
        return self._t(u, "adm_master_invite", name=tenant.masters[p["master_id"]].name, hours=INVITE_HOURS,
                       link=link)

    async def _do_export(self, u: StaffUser, p: dict) -> str:
        from .admin_panel import XLSX_MIME
        from .telegram import NetworkError, TelegramError

        export = self.app.build_export(u.tenant, p["days"])
        if export is None:
            raise self._err(u, "export_empty")
        filename, content, caption = export
        try:
            await self.app.apis[u.tenant.slug].send_document(u.chat_id, filename, content, caption=caption,
                                                             mime=XLSX_MIME)
        except (TelegramError, NetworkError):
            raise self._err(u, "no_telegram") from None
        return self._t(u, "staff_done_export")

    def resume_ai(self, u: StaffUser, client_id: int) -> None:
        """Повернути клієнта AI (зняти паузу після передачі розмови людині)."""
        if not u.is_owner:
            raise self._err(u, "owner_only")
        client = self.db.get_client(self._int(u, client_id))
        if client is None or client["tenant"] != u.tenant.slug:
            raise self._err(u, "not_found")
        self.db.set_client_field(client["id"], "paused_until", None)


# ================================================================ AI для персоналу

RULES = """Ти — помічник персоналу закладу «{name}». З тобою говорить {who}. Людина часто зайнята (стриже клієнта) і говорить голосом: текст розпізнано автоматично, тож імена й слова можуть бути з помилками — шукай найсхожіше серед записів (get_schedule) і клієнтів (find_client).

## Як відповідати
- Мовою, якою говорить людина. Дуже коротко: 1–2 речення, бо відповідь часто читають уголос.
- Без списків, markdown, емодзі й номерів записів. Час кажи як «о 14:30», дні — «завтра», «у пʼятницю 30 жовтня».
- Якщо записів багато — назви кількість і найближчі 3–4.

## Факти
- Розклад, клієнти, вільний час, закритий час, звіт — лише з інструментів. Нічого не вигадуй.
- Сьогодні й завтра — див. «Зараз» нижче. Дати передавай в інструменти як YYYY-MM-DD, час — HH:MM.
- Якщо послуга не названа, а для дії вона потрібна, — уточни одним питанням.

## Зміни
Закрити чи відкрити час, записати клієнта, перенести, скасувати, позначити неявку, написати клієнту, змінити ціну, увімкнути чи вимкнути AI для клієнтів, повернути клієнта AI, запросити майстра, надіслати Excel — лише через інструменти. Вони НЕ виконують дію, а готують її і показують людині картку з кнопкою.
Після виклику одним реченням перекажи, що буде зроблено, і спитай: «Підтверджуєте?». Виконає система, коли людина скаже «так» або натисне кнопку. Не кажи, що вже зроблено.
Якщо інструмент повернув помилку — поясни простими словами й запропонуй варіант (інший час — через get_free_slots).
{rights}

## Межі
Лише робота цього закладу: розклад, записи, клієнти, ціни, звіти. На інше — одне речення, що ти допомагаєш лише з цим.
Повідомлення, що починаються з «[Системна подія]», надсилає система."""

RIGHTS_OWNER = ("Ти говориш із власником: йому можна все — будь-який майстер, перенесення, скасування, повідомлення "
                "клієнтам, ціни, AI для клієнтів, запрошення майстрів, звіти й Excel.")
RIGHTS_MASTER = ("Ти говориш із майстром {master}: він керує лише своїм розкладом — бачить свої записи, закриває "
                 "й відкриває свій час, записує клієнтів до себе, позначає неявку. Переносити й скасовувати записи "
                 "клієнтів може лише власник — так і скажи, якщо майстер просить.")


def staff_tools() -> list[dict]:
    def tool(name: str, description: str, props: dict, required: list[str] | None = None) -> dict:
        return {"name": name, "description": description,
                "input_schema": {"type": "object", "properties": props, "required": required or []}}

    date_p = {"type": "string", "description": "Дата YYYY-MM-DD"}
    time_p = {"type": "string", "description": "Час HH:MM"}
    master_p = {"type": "string", "description": "id майстра (з розділу «Майстри» чи довідника конектора)"}
    return [
        tool("get_schedule", "Записи, закритий час і години роботи на день або кілька днів.",
             {"date": {**date_p, "description": "Перший день, YYYY-MM-DD (за замовчуванням сьогодні)"},
              "days": {"type": "integer", "description": "Скільки днів, 1–14 (за замовчуванням 1)"},
              "master_id": {**master_p, "description": "Лише цей майстер (для власника; інакше всі)"}}),
        tool("get_free_slots", "Вільний час для послуги на день.",
             {"service_id": {"type": "string", "description": "id послуги з розділу «Послуги»"},
              "date": date_p, "master_id": master_p}, ["service_id", "date"]),
        tool("find_client", "Знайти клієнта за імʼям, частиною імені або номером телефону; з його майбутніми записами.",
             {"query": {"type": "string"}}, ["query"]),
        tool("get_report", "Підсумки: візити, виручка, неявки, скасування, по майстрах; від 7 днів — і робота бота "
                           "(записи через AI, уночі, вартість AI). days — довільна кількість останніх днів.",
             {"period": {"type": "string", "enum": ["today", "yesterday", "tomorrow", "week", "month"]},
              "days": {"type": "integer", "description": "Останні N днів, 1–3650 (замість period)"}}),
        tool("get_shop", "Стан закладу (лише власник): чи відповідає AI клієнтам, послуги з цінами "
                         "(поточна й з файлу налаштувань), майстри та чи підключені вони до бота.", {}),
        tool("list_blocks", "Увесь майбутній закритий час (вихідні, перерви).", {}),
        tool("get_client_chats", "Останні розмови клієнтів із ботом і хто чекає на відповідь людини (лише власник).",
             {}),
        tool("block_time", "Підготувати: закрити час для запису (вихідний, перерва). Без time_from/time_to — "
                           "увесь день. Для власника master_id обовʼязковий: id майстра або \"all\" — для всіх.",
             {"date": date_p, "time_from": time_p, "time_to": time_p, "master_id": master_p,
              "note": {"type": "string", "description": "Причина, коротко"}}, ["date"]),
        tool("unblock_time", "Підготувати: відкрити закритий час назад (block_id з get_schedule чи list_blocks).",
             {"block_id": {"type": "integer"}}, ["block_id"]),
        tool("create_booking", "Підготувати: записати клієнта. Відомого клієнта — через client_id (find_client), "
                               "нового — client_name і, якщо відомо, client_phone.",
             {"service_id": {"type": "string"}, "date": date_p, "time": time_p, "master_id": master_p,
              "client_id": {"type": "integer"}, "client_name": {"type": "string"},
              "client_phone": {"type": "string"}, "note": {"type": "string"}},
             ["service_id", "date", "time"]),
        tool("reschedule_booking", "Підготувати: перенести запис (лише власник).",
             {"booking_id": {"type": "integer"}, "date": date_p, "time": time_p, "master_id": master_p},
             ["booking_id", "date", "time"]),
        tool("cancel_booking", "Підготувати: скасувати запис (лише власник). Клієнт отримає повідомлення.",
             {"booking_id": {"type": "integer"}}, ["booking_id"]),
        tool("mark_no_show", "Підготувати: позначити, що клієнт не прийшов (сьогоднішній або минулий запис).",
             {"booking_id": {"type": "integer"}}, ["booking_id"]),
        tool("message_client", "Підготувати: написати клієнту від імені закладу в його чат (лише власник).",
             {"client_id": {"type": "integer"}, "text": {"type": "string"}}, ["client_id", "text"]),
        tool("set_price", "Підготувати: змінити ціну послуги (лише власник). Без price — повернути ціну з файлу "
                          "налаштувань. Ціни комбінацій із додатками перераховуються самі.",
             {"service_id": {"type": "string"}, "price": {"type": "number"}}, ["service_id"]),
        tool("set_client_ai", "Підготувати: увімкнути (on=true) чи вимкнути (on=false) AI, що відповідає клієнтам. "
                              "Вимкнений — усі повідомлення клієнтів пересилаються власнику (лише власник).",
             {"on": {"type": "boolean"}}, ["on"]),
        tool("return_client_to_ai", "Підготувати: повернути клієнта AI-помічнику, якщо розмову було передано людині "
                                    "(waiting_for_human у get_client_chats; лише власник).",
             {"client_id": {"type": "integer"}}, ["client_id"]),
        tool("invite_master", "Підготувати: нове одноразове посилання, яким майстер підключиться до бота (лише власник).",
             {"master_id": master_p}, ["master_id"]),
        tool("export_bookings", "Підготувати: надіслати власнику в Telegram Excel-файл із записами за останні days днів "
                                "і всіма майбутніми (лише власник).",
             {"days": {"type": "integer", "description": "1–3650, за замовчуванням 30"}}),
    ]


TOOL_KINDS = {"block_time": "block", "unblock_time": "unblock", "create_booking": "book",
              "reschedule_booking": "reschedule", "cancel_booking": "cancel", "mark_no_show": "no_show",
              "message_client": "message", "set_price": "price", "set_client_ai": "client_ai",
              "return_client_to_ai": "resume_client", "invite_master": "invite", "export_bookings": "export"}


def _plain(text) -> str:
    """Для порівняння імен: без регістру, наголосів і зайвих пробілів («Máté» = «mate»)."""
    decomposed = unicodedata.normalize("NFKD", str(text or "")).casefold()
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def resolve_ids(tenant: Tenant, args: dict) -> dict:
    """Зовнішній AI (конектор) часто передає імʼя майстра чи назву послуги замість id — переводимо в id.
    Невідоме значення лишаємо як є: перевірка далі поверне зрозумілу помилку."""
    args = dict(args)
    for key, items, field_name in (("master_id", tenant.masters, "name"), ("service_id", tenant.services, "title")):
        value = args.get(key)
        if not isinstance(value, str) or not value or value in items or value in ("any", "all", "*"):
            continue
        wanted = _plain(value)
        found = [i for i, item in items.items() if wanted == _plain(i)
                 or wanted in {_plain(item.tr(field_name, lang)) for lang in tenant.languages}]
        if len(found) == 1:
            args[key] = found[0]
    return args


class StaffTools:
    """Виконує виклики інструментів моделі (і MCP-клієнтів) від імені людини з персоналу."""

    def __init__(self, ops: StaffOps, u: StaffUser):
        self.ops = ops
        self.u = u
        self.action: dict | None = None  # підготовлена дія (остання)

    def run(self, name: str, args) -> dict:
        args = resolve_ids(self.u.tenant, args) if isinstance(args, dict) else {}
        ops, u = self.ops, self.u
        try:
            if name == "get_schedule":
                return ops.schedule(u, args.get("date"), args.get("days") or 1, args.get("master_id"))
            if name == "get_free_slots":
                return ops.free_slots(u, str(args.get("service_id") or ""), args.get("date"), args.get("master_id"))
            if name == "find_client":
                return ops.find_clients(u, str(args.get("query") or ""))
            if name == "get_report":
                return ops.report(u, str(args.get("period") or "today"), args.get("days"))
            if name == "list_blocks":
                return ops.blocks(u)
            if name == "get_client_chats":
                return ops.chats(u)
            if name == "get_shop":
                return ops.shop(u)
            if name in TOOL_KINDS:
                self.action = ops.propose(u, TOOL_KINDS[name], args)
                return {"status": "awaiting_confirmation", "action_id": self.action["action_id"],
                        "summary": self.action["summary"],
                        "note": "Дію ще НЕ виконано. Перекажи її людині й спитай, чи підтверджує."}
        except StaffError as e:
            return {"error": e.code, "message": e.message}
        except Exception:
            log.exception("Помилка інструмента персоналу %s", name)
            return {"error": "internal", "message": "Внутрішня помилка."}
        return {"error": "unknown_tool", "message": f"Інструмента {name} немає."}


@dataclass
class AgentOutcome:
    text: str = ""
    action: dict | None = None
    error: str | None = None
    tools_used: list[str] = field(default_factory=list)


class StaffAgent:
    def __init__(self, settings, llm):
        self.settings = settings
        self.llm = llm

    def system(self, u: StaffUser, db) -> list[dict]:
        tenant = u.tenant
        if u.is_owner:
            who = "власник закладу" + (f" (він же майстер {tenant.masters[u.master_id].name})" if u.master_id else "")
            rights = RIGHTS_OWNER
        else:
            who = f"майстер {tenant.masters[u.master_id].name}"
            rights = RIGHTS_MASTER.format(master=tenant.masters[u.master_id].name)
        static = RULES.format(name=tenant.name, who=who, rights=rights)
        now = tenant.now()
        lines = ["## Зараз", f"Сьогодні {WEEKDAYS_FULL_UK[now.weekday()]}, {now.date().isoformat()}, "
                 f"зараз {fmt_hhmm(now)}. Завтра — "
                 f"{(now.date() + timedelta(days=1)).isoformat()} ({WEEKDAYS_FULL_UK[(now.weekday() + 1) % 7]}).",
                 "", "## Майстри (id — імʼя — графік)"]
        for m in tenant.masters.values():
            lines.append(f"- {m.id} — {m.name}" + (" (це співрозмовник)" if m.id == u.master_id else "")
                         + f" — {tenant.schedule_summary('uk', m).replace(chr(10), '; ')}")
        lines += ["", "## Послуги (id — назва — хвилин — ціна)"]
        for s in tenant.services.values():
            if not (s.hidden and not s.base_id):
                lines.append(f"- {s.id} — {s.title} — {s.duration} — {tenant.price_str(s.price)}")
        name = u.name(db)
        if name:
            lines += ["", f"Імʼя співрозмовника: {name}."]
        return [{"type": "text", "text": static, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "\n".join(lines)}]

    async def reply(self, ops: StaffOps, u: StaffUser, text: str) -> AgentOutcome:
        db, tenant = ops.db, u.tenant
        now = tenant.now()
        history = prepare_history(db.load_history(u.client_id, now - timedelta(hours=self.settings.history_hours),
                                                  self.settings.history_messages))
        turn: list[dict] = [{"role": "user", "content": text}]
        tools = StaffTools(ops, u)
        outcome = AgentOutcome()
        system = self.system(u, db)
        for round_no in range(self.settings.max_tool_rounds + 1):
            payload = {"model": self.settings.model, "max_tokens": self.settings.max_tokens, "system": system,
                       "messages": merge_roles(history + turn), "tools": staff_tools()}
            if self.settings.effort:
                payload["output_config"] = {"effort": self.settings.effort}
            if self.settings.thinking == "disabled":
                payload["thinking"] = {"type": "disabled"}
            if round_no == self.settings.max_tool_rounds:
                payload["tool_choice"] = {"type": "none"}
            try:
                response = await self.llm.create(payload)
            except LLMError as e:
                outcome.error = str(e)
                break
            self._log_usage(db, u, response)
            content = sanitize_assistant_blocks(response.get("content") or [])
            tool_uses = [b for b in content if b["type"] == "tool_use"]
            if response.get("stop_reason") == "tool_use" and tool_uses:
                turn.append({"role": "assistant", "content": content})
                results = []
                for tu in tool_uses:
                    outcome.tools_used.append(tu["name"])
                    out = tools.run(tu["name"], tu["input"])
                    block = {"type": "tool_result", "tool_use_id": tu["id"],
                             "content": json.dumps(out, ensure_ascii=False, default=str)}
                    if "error" in out:
                        block["is_error"] = True
                    results.append(block)
                turn.append({"role": "user", "content": results})
                continue
            final = [b for b in content if b["type"] != "tool_use"]
            if final:
                turn.append({"role": "assistant", "content": final})
            break
        for m in reversed(turn):
            if m["role"] == "assistant":
                texts = [b["text"] for b in m["content"] if isinstance(b, dict) and b.get("type") == "text"
                         and b.get("text")]
                if texts:
                    outcome.text = clean_ai_text("\n".join(texts))
                    break
        outcome.action = tools.action
        if not outcome.error:
            for m in turn:
                content = strip_thinking(m["content"]) if m["role"] == "assistant" else m["content"]
                if content:
                    db.add_history(tenant.slug, u.client_id, m["role"], content, now)
        return outcome

    def _log_usage(self, db, u: StaffUser, response: dict) -> None:
        usage = response.get("usage") or {}
        db.log_event(u.tenant.slug, u.client_id, "ai_usage", u.tenant.now(), {
            "input": usage.get("input_tokens") or 0, "output": usage.get("output_tokens") or 0,
            "cache_read": usage.get("cache_read_input_tokens") or 0,
            "cache_write": usage.get("cache_creation_input_tokens") or 0,
            "model": response.get("model") or self.settings.model, "staff": True})


class StaffAssistant:
    """Вхід для всіх каналів: «так»/«ні» на підготовлену дію — без AI; решта — питання до StaffAgent."""

    def __init__(self, app, llm=None):
        self.app = app
        self.ops = StaffOps(app)
        self.agent = StaffAgent(app.settings, llm) if llm is not None else None

    def _t(self, u: StaffUser, key: str, **kw) -> str:
        return strip_tags(u.tenant.t(u.tenant.lang, key, **kw))

    def over_budget(self, u: StaffUser) -> bool:
        tenant = u.tenant
        limit = tenant.ai_daily_token_limit if tenant.ai_daily_token_limit is not None \
            else self.app.settings.daily_token_limit
        return bool(limit) and self.app.db.tokens_since(
            tenant.slug, datetime.combine(tenant.today(), time.min)) >= limit

    async def confirm(self, u: StaffUser, action_id: str) -> StaffReply:
        try:
            result = await self.ops.execute(u, action_id)
        except StaffError as e:
            return StaffReply(text=e.message, error=e.code)
        return StaffReply(text=result["text"], done=True)

    async def ask(self, u: StaffUser, text: str) -> StaffReply:
        text = short(text or "", 1500)
        pending = self.ops.pending(u)
        if pending and is_affirmative(text):
            return await self.confirm(u, pending)
        if pending and is_negative(text):
            self.ops.drop(u, pending)
            return StaffReply(text=self._t(u, "staff_declined"))
        if self.agent is None:
            return StaffReply(text=self._t(u, "staff_ai_off"), error="no_ai")
        if self.over_budget(u):
            return StaffReply(text=self._t(u, "staff_ai_off"), error="budget")
        self.app.db.log_event(u.tenant.slug, u.client_id, "staff_ai", u.tenant.now())
        outcome = await self.agent.reply(self.ops, u, text)
        if outcome.error:
            log.warning("[%s] AI персоналу: %s", u.tenant.name, outcome.error)
            await self.app.alert_tech(u.tenant, outcome.error)
            return StaffReply(text=self._t(u, "ai_error"), error="ai")
        reply = StaffReply(text=outcome.text, action=outcome.action)
        if outcome.action and not reply.text:
            reply.text = outcome.action["summary"] + "\n" + self._t(u, "staff_confirm_q")
        return reply
