"""Міні-застосунок онлайн-запису: сторінка barberbot/webapp/index.html і JSON API для неї.

Відкривається як Telegram Mini App (кнопка меню бота), у Messenger (кнопка з підписаним посиланням) або просто
за посиланням (біо Instagram, Google Maps, сайт). Запис іде через ту саму BookingService і ті самі
сповіщення, що й кнопки в боті (BotApp.announce_booking).

Хто записується:
- Telegram — перевіряємо підпис initData токеном бота, клієнт той самий, що й у чаті з ботом;
- Messenger/Instagram — посилання з підписом ?u=<чат>.<підпис>, який видає бот;
- без входу — ім'я й телефон із форми (клієнт без чату, як записаний адміністратором).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import time as monotime
import urllib.parse
from collections import defaultdict, deque
from datetime import date, datetime
from pathlib import Path

from . import clock
from .booking import BookingError
from .config import fmt_hhmm, parse_hhmm
from .util import normalize_phone, short
from .web import Response

log = logging.getLogger("barberbot.webapp")

PAGE = Path(__file__).with_name("webapp") / "index.html"
PATH_RE = re.compile(r"^/app/([A-Za-z0-9_-]{1,40})/(?:(api)/([a-z]+))?$")
BOOKINGS_PER_IP_HOUR = 10
INIT_DATA_MAX_AGE = 24 * 3600


def telegram_user(bot_token: str, init_data: str, now: float | None = None) -> dict | None:
    """Користувач Telegram Mini App, якщо підпис initData справжній (див. core.telegram.org/bots/webapps)."""
    if not init_data:
        return None
    pairs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", "")
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode("utf-8"), hashlib.sha256).hexdigest()
    if not received or not hmac.compare_digest(expected, received):
        return None
    now = now if now is not None else clock.utcnow().timestamp()
    if now - int(pairs.get("auth_date") or 0) > INIT_DATA_MAX_AGE:
        return None
    try:
        user = json.loads(pairs.get("user") or "")
    except ValueError:
        return None
    return user if isinstance(user, dict) and user.get("id") else None


def json_response(data: dict, status: int = 200) -> Response:
    return Response(status, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8",
                    {"Cache-Control": "no-store"})


class WebApp:
    def __init__(self, app):
        self.app = app
        self.settings = app.settings
        self.db = app.db
        secret = self.db.kv_get("_web", "secret")
        if not secret:
            secret = secrets.token_hex(32)
            self.db.kv_set("_web", "secret", secret)
        self.secret = secret.encode("utf-8")
        self.recent: dict[str, deque] = defaultdict(deque)  # IP → час останніх записів

    # ---- посилання
    def sign(self, slug: str, chat_id: int) -> str:
        sig = hmac.new(self.secret, f"{slug}:{chat_id}".encode(), hashlib.sha256).hexdigest()[:32]
        return f"{chat_id}.{sig}"

    def verify(self, slug: str, token: str) -> int | None:
        chat, _, _ = (token or "").partition(".")
        if not chat.lstrip("-").isdigit():
            return None
        return int(chat) if hmac.compare_digest(self.sign(slug, int(chat)), token) else None

    def url(self, tenant, chat_id: int | None = None, lang: str | None = None) -> str:
        """Посилання на запис. З chat_id — підписане: застосунок знатиме, хто записується (Messenger/Instagram)."""
        query = {}
        if lang:
            query["lang"] = lang
        if chat_id is not None:
            query["u"] = self.sign(tenant.slug, chat_id)
        return f"{self.settings.web_base_url}/app/{tenant.slug}/" + (f"?{urllib.parse.urlencode(query)}" if query else "")

    # ---- маршрути
    async def handle(self, method: str, target: str, headers: dict[str, str], body: bytes) -> Response:
        parts = urllib.parse.urlsplit(target)
        m = PATH_RE.match(parts.path)
        if not m:
            if re.fullmatch(r"/app/[A-Za-z0-9_-]{1,40}", parts.path):
                return Response(301, "", headers={"Location": parts.path + "/" + (f"?{parts.query}" if parts.query else "")})
            return Response(404, "not found")
        tenant = self.app.tenants.get(m.group(1))
        if tenant is None:
            return Response(404, "not found")
        if not m.group(2):
            if method != "GET":
                return Response(405, "method not allowed")
            return Response(200, PAGE.read_bytes(), "text/html; charset=utf-8", {"Cache-Control": "no-cache"})
        query = dict(urllib.parse.parse_qsl(parts.query))
        lang = query.get("lang") if query.get("lang") in tenant.languages else tenant.lang
        try:
            if m.group(3) == "config" and method == "GET":
                return json_response(self.config(tenant, lang, headers, query))
            if m.group(3) == "days" and method == "GET":
                return json_response(self.days(tenant, query))
            if m.group(3) == "slots" and method == "GET":
                return json_response(self.slots(tenant, query))
            if m.group(3) == "book" and method == "POST":
                return await self.book(tenant, headers, body)
        except BookingError:
            return json_response({"error": "bad_request"}, 400)
        except (KeyError, ValueError):
            return json_response({"error": "bad_request"}, 400)
        return Response(404, "not found")

    # ---- хто це
    def identify(self, tenant, headers: dict[str, str], token: str | None) -> tuple[int | None, dict]:
        """(чат, дані користувача) для Telegram чи Meta; (None, {}) — без входу."""
        user = telegram_user(tenant.bot_token, headers.get("x-telegram-init-data", ""))
        if user:
            return int(user["id"]), user
        chat = self.verify(tenant.slug, token or headers.get("x-booking-token", ""))
        if chat is not None:
            client = self.db.get_client_by_tg(tenant.slug, chat)
            if client is not None:
                return chat, {"id": chat, "first_name": client["first_name"], "last_name": client["last_name"],
                              "username": client["username"], "language_code": client["lang"]}
        return None, {}

    # ---- дані
    def config(self, tenant, lang: str, headers: dict[str, str], query: dict) -> dict:
        def svc(s):
            combos = [c for c in tenant.services.values() if c.base_id == s.id]
            return {"id": s.id, "title": s.tr("title", lang), "icon": s.icon, "duration": s.duration,
                    "price": s.price, "price_text": tenant.price_str(s.price), "description": s.tr("description", lang),
                    "addons": [{"id": c.id, "title": tenant.services[c.addon_id].tr("title", lang),
                                "duration": tenant.services[c.addon_id].duration,
                                "price": tenant.services[c.addon_id].price,
                                "price_text": "+" + tenant.price_str(tenant.services[c.addon_id].price)} for c in combos]}
        groups = [{"id": g, "title": ss[0].tr("group", lang) if g else "", "services": [svc(s) for s in ss]}
                  for g, ss in tenant.service_groups()]
        chat, _ = self.identify(tenant, headers, query.get("u"))
        client = self.db.get_client_by_tg(tenant.slug, chat) if chat is not None else None
        return {
            "name": tenant.name, "lang": lang, "languages": tenant.languages, "price_format": tenant.price_format,
            "address": tenant.info_in("address", lang), "phone": tenant.info.get("phone", ""),
            "require_phone": tenant.require_phone, "groups": groups,
            "masters": [{"id": m.id, "name": m.tr("name", lang), "about": m.tr("about", lang), "services": m.services}
                        for m in tenant.masters.values()],
            "client": {"known": chat is not None,
                       "name": (client["name"] or client["first_name"] or "") if client else "",
                       "phone": (client["phone"] or "") if client else ""},
        }

    def days(self, tenant, query: dict) -> dict:
        booking = self.app.bookings[tenant.slug]
        service, master = query["service"], query.get("master") or "any"
        return {"days": [{"date": d.isoformat(), "open": bool(booking.free_slots(service, master, d))}
                         for d in booking.horizon_days()]}

    def slots(self, tenant, query: dict) -> dict:
        booking = self.app.bookings[tenant.slug]
        day = date.fromisoformat(query["date"])
        return {"times": list(booking.free_slots(query["service"], query.get("master") or "any", day))}

    # ---- запис
    def _rate_ok(self, ip: str) -> bool:
        q, now = self.recent[ip], monotime.monotonic()
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= BOOKINGS_PER_IP_HOUR:
            return False
        q.append(now)
        return True

    async def book(self, tenant, headers: dict[str, str], body: bytes) -> Response:
        from .app import Ctx, strip_html  # тут, щоб уникнути циклічного імпорту

        data = json.loads(body.decode("utf-8") or "{}")
        lang = data.get("lang") if data.get("lang") in tenant.languages else tenant.lang
        t = lambda key, **kw: strip_html(tenant.t(lang, key, **kw))  # noqa: E731
        ip = (headers.get("x-forwarded-for") or "local").split(",")[0].strip()
        if not self._rate_ok(ip):
            return json_response({"error": "rate_limited", "message": t("rate_limited")}, 429)

        service_id, master_id = str(data["service"]), str(data.get("master") or "any")
        start = datetime.combine(date.fromisoformat(data["date"]), parse_hhmm(data["time"]))
        name = short(str(data.get("name") or "").strip(), 60)
        phone_raw = str(data.get("phone") or "").strip()
        phone = normalize_phone(phone_raw) if phone_raw else None

        chat, user = self.identify(tenant, headers, data.get("token"))
        db, now = self.db, tenant.now()
        if chat is None:
            if len(name) < 2 or not phone:
                return json_response({"error": "need_contact", "message": t("bad_phone")}, 400)
            client = db.find_client_by_phone(tenant.slug, phone) or db.create_offline_client(tenant.slug, name, phone, now)
            chat = client["tg_id"]
            user = {"id": chat, "first_name": client["first_name"] or name, "last_name": client["last_name"],
                    "username": client["username"], "language_code": lang}
        else:
            user = {**user, "language_code": lang}
            if phone_raw and not phone:
                return json_response({"error": "bad_phone", "message": t("bad_phone")}, 400)

        async with self.app.locks[(tenant.slug, chat)]:
            ctx = Ctx(self.app, tenant, user, chat)
            ctx.lang = lang
            if phone and not ctx.client["phone"]:
                db.set_client_phone(ctx.client_id, phone)
            if name and not ctx.client["name"]:
                db.set_client_field(ctx.client_id, "name", name)
            ctx.refresh()
            if tenant.require_phone and not ctx.client["phone"]:
                return json_response({"error": "need_phone", "message": t("bad_phone")}, 400)
            try:
                b = ctx.booking.create(ctx.client_id, service_id, master_id, start, "buttons")
            except BookingError as e:
                key = {"duplicate": "already_booked", "week_limit": "week_limit", "too_many": "too_many_active",
                       "slot_taken": "slot_taken", "past": "slot_taken", "too_soon": "slot_taken",
                       "too_far": "slot_taken"}.get(e.code, "booking_error")
                return json_response({"error": e.code, "message": t(key, limit=e.info.get("limit", 0),
                                                                     count=e.info.get("count", 0))}, 409)
            await self.app.announce_booking(ctx, b, "web")
        names = tenant.booking_names(b, lang)
        prepay = ""
        if b["prepay"] == "waiting":
            prepay = strip_html(self.app.prepay_block(ctx, b)).strip()
        log.info("[%s] Онлайн-запис №%s (%s)", tenant.name, b["id"], "чат" if chat > 0 else "без чату")
        return json_response({"ok": True, "booking": {
            "id": b["id"], "service": names["service"], "master": names["master"],
            "day": tenant.day_label(start.date(), lang), "time": fmt_hhmm(start),
            "price_text": tenant.price_str(b["price"]), "prepay": prepay, "in_chat": chat > 0}})
