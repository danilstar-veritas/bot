"""Telegram-бот: меню, запис кнопками, AI-чат, передача власнику, адмін-команди.

Один процес обслуговує кілька закладів: кожен заклад має свій бот (токен)
і свій файл налаштувань у config/tenants/.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta

from .agent import Agent, add_note, history_transcript
from .booking import BookingError, BookingService
from .config import RANGE_RE, ConfigError, Settings, Tenant, fmt_hhmm, load_tenant, parse_hhmm, parse_user_date
from .db import DB, dt_str, parse_dt
from .stats import compute_stats
from .telegram import NetworkError, TelegramAPI, TelegramError, chunk_text, ibtn, inline_kb, reply_kb, url_btn
from .texts import Raw
from .util import is_affirmative, normalize_phone, short

log = logging.getLogger("barberbot")

ADMIN_COMMANDS = ["start", "admin", "today", "tomorrow", "week", "all", "stats", "block", "blocks", "pause", "resume",
                  "reload", "myid"]
PENDING_TTL = timedelta(minutes=30)
POLL_TIMEOUT = 25


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


def _rows(buttons: list[dict], per_row: int) -> list[list[dict]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


class Ctx:
    """Контекст обробки одного повідомлення чи натискання кнопки."""

    def __init__(self, app: "BotApp", tenant: Tenant, user: dict, chat_id: int):
        self.app = app
        self.tenant = tenant
        self.api = app.apis[tenant.slug]
        self.booking = app.bookings[tenant.slug]
        self.db = app.db
        self.user_id = int(user["id"])
        self.chat_id = chat_id
        self.lang = tenant.lang_for(user.get("language_code"))
        self.client = self.db.upsert_client(tenant.slug, self.user_id, user.get("first_name"), user.get("last_name"),
                                            user.get("username"), self.lang, tenant.now())
        self.is_admin = self.user_id in tenant.admins

    @property
    def key(self) -> tuple[str, int]:
        return self.tenant.slug, self.user_id

    @property
    def client_id(self) -> int:
        return self.client["id"]

    def refresh(self) -> None:
        self.client = self.db.get_client(self.client_id)

    def t(self, key: str, **kw) -> str:
        return self.tenant.t(self.lang, key, **kw)

    def at(self, key: str, **kw) -> str:
        """Текст для адміністратора (основна мова закладу)."""
        return self.tenant.t(self.tenant.lang, key, **kw)

    async def send(self, text: str, kb: dict | None = None, parse_mode: str | None = "HTML") -> dict | None:
        return await self.app.send(self.tenant, self.chat_id, text, kb, parse_mode)

    async def edit(self, message_id: int, text: str, kb: dict | None = None) -> bool:
        params = {"chat_id": self.chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML",
                  "link_preview_options": {"is_disabled": True}, "reply_markup": kb}
        try:
            await self.api.call("editMessageText", **params)
            return True
        except TelegramError as e:
            if e.not_modified:
                return True
            log.info("Не вдалося змінити повідомлення (%s), надсилаю нове", e.description)
            return False
        except NetworkError as e:
            log.warning("Мережа: %s", e)
            return False

    async def show(self, message_id: int | None, text: str, kb: dict | None = None) -> int | None:
        """Оновити повідомлення з кнопками (крок запису) або надіслати нове. Повертає його id."""
        if message_id and await self.edit(message_id, text, kb):
            return message_id
        sent = await self.send(text, kb)
        return sent["message_id"] if sent else None

    async def clear_kb(self, message_id: int | None) -> None:
        if not message_id:
            return
        try:
            await self.api.call("editMessageReplyMarkup", chat_id=self.chat_id, message_id=message_id)
        except (TelegramError, NetworkError):
            pass


class BotApp:
    def __init__(self, settings: Settings, tenants: list[Tenant], db: DB, llm=None, api_factory=None):
        self.settings = settings
        self.db = db
        self.tenants: dict[str, Tenant] = {t.slug: t for t in tenants if t.enabled}
        factory = api_factory or (lambda t: TelegramAPI(t.bot_token, settings.telegram_api_base))
        self.apis = {slug: factory(t) for slug, t in self.tenants.items()}
        self.bookings = {slug: BookingService(t, db) for slug, t in self.tenants.items()}
        self.agent = Agent(settings, llm) if llm is not None else None
        self.states: dict[tuple[str, int], tuple[str, dict]] = {}
        # Остання картка від AI, яку клієнт може підтвердити текстом «так»: (дані кнопки, до коли, id картки)
        self.pending: dict[tuple[str, int], tuple[str, datetime, int | None]] = {}
        self.locks: dict[tuple[str, int], asyncio.Lock] = defaultdict(asyncio.Lock)
        self.last_alert: dict[str, datetime] = {}
        self.last_ack: dict[tuple[str, int], datetime] = {}
        self.usernames: dict[str, str] = {}
        self.inflight: set[asyncio.Task] = set()
        self.stopping = False
        self.stop_event = asyncio.Event()
        self.poll_timeout = POLL_TIMEOUT

    # ================================================================ запуск
    async def run(self) -> None:
        from .scheduler import Scheduler

        tasks = [asyncio.create_task(self.poll(slug), name=f"poll:{slug}") for slug in self.tenants]
        tasks.append(asyncio.create_task(Scheduler(self).run(), name="scheduler"))
        try:
            await self.stop_event.wait()
        finally:
            self.stopping = True
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if self.inflight:
                await asyncio.wait(self.inflight, timeout=5)

    def stop(self) -> None:
        self.stopping = True
        self.stop_event.set()

    async def poll(self, slug: str) -> None:
        tenant = self.tenants[slug]
        api = self.apis[slug]
        delay = 2
        while not self.stopping:
            try:
                me = await api.call("getMe")
                break
            except TelegramError as e:
                if e.code in (401, 404):
                    log.error("[%s] Telegram не приймає токен бота — перевірте bot_token у %s", tenant.name,
                              tenant.path.name)
                    return
                log.warning("[%s] getMe: %s", tenant.name, e)
            except NetworkError as e:
                log.warning("[%s] Немає зв'язку з Telegram: %s", tenant.name, e)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
        else:
            return
        self.usernames[slug] = me.get("username", "")
        log.info("[%s] Бот @%s запущено", tenant.name, self.usernames[slug])
        try:
            await api.call("deleteWebhook")
        except (TelegramError, NetworkError):
            pass
        await self.setup_commands(slug)

        offset = None
        delay = 2
        while not self.stopping:
            try:
                updates = await api.call("getUpdates", _timeout=self.poll_timeout + 15, _retries=0, offset=offset,
                                         timeout=self.poll_timeout, allowed_updates=["message", "callback_query"])
                delay = 2
            except TelegramError as e:
                if e.code == 409:
                    log.error("[%s] Цей бот уже запущено в іншому місці (або встановлено webhook). "
                              "Зупиніть іншу копію.", tenant.name)
                    await asyncio.sleep(10)
                elif e.code in (401, 404):
                    log.error("[%s] Токен бота більше не дійсний.", tenant.name)
                    return
                else:
                    log.warning("[%s] getUpdates: %s", tenant.name, e)
                    await asyncio.sleep(3)
                continue
            except NetworkError as e:
                log.warning("[%s] Немає зв'язку з Telegram: %s", tenant.name, e)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            for update in updates or []:
                offset = update["update_id"] + 1
                self.spawn(self.safe_handle(slug, update))

    def spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self.inflight.add(task)
        task.add_done_callback(self.inflight.discard)
        return task

    async def setup_commands(self, slug: str) -> None:
        tenant, api = self.tenants[slug], self.apis[slug]
        try:
            for lang in tenant.languages:
                await api.call("setMyCommands", commands=[{"command": "start", "description": tenant.t(lang, "cmd_start")}],
                               language_code=lang)
            await api.call("setMyCommands",
                           commands=[{"command": "start", "description": tenant.t(tenant.lang, "cmd_start")}])
        except (TelegramError, NetworkError) as e:
            log.warning("[%s] setMyCommands: %s", tenant.name, e)
        admin_cmds = [{"command": c, "description": tenant.t(tenant.lang, f"cmd_{c}")} for c in ADMIN_COMMANDS]
        for admin in tenant.admins:
            try:
                await api.call("setMyCommands", commands=admin_cmds, scope={"type": "chat", "chat_id": admin})
            except (TelegramError, NetworkError):
                log.info("[%s] Адмін %s ще не натиснув /start у боті — меню команд з'явиться пізніше",
                         tenant.name, admin)

    async def safe_handle(self, slug: str, update: dict) -> None:
        try:
            await self.handle_update(slug, update)
        except Exception:
            log.exception("Помилка обробки оновлення %s", update.get("update_id"))

    async def handle_update(self, slug: str, update: dict) -> None:
        tenant = self.tenants.get(slug)
        if tenant is None:
            return
        if "message" in update:
            msg = update["message"]
            user = msg.get("from") or {}
            if (msg.get("chat") or {}).get("type") != "private" or not user.get("id") or user.get("is_bot"):
                return
            async with self.locks[(slug, user["id"])]:
                ctx = Ctx(self, self.tenants[slug], user, msg["chat"]["id"])
                await self.on_message(ctx, msg)
        elif "callback_query" in update:
            cq = update["callback_query"]
            user = cq.get("from") or {}
            if not user.get("id"):
                return
            msg = cq.get("message") or {}
            chat = msg.get("chat") or {}
            if chat and chat.get("type") != "private":
                return
            async with self.locks[(slug, user["id"])]:
                ctx = Ctx(self, self.tenants[slug], user, chat.get("id", user["id"]))
                await self.on_callback(ctx, cq)

    # ================================================================ надсилання
    async def send(self, tenant: Tenant, chat_id: int, text: str, kb: dict | None = None,
                   parse_mode: str | None = "HTML") -> dict | None:
        api = self.apis[tenant.slug]
        chunks = chunk_text(text)
        last = None
        for i, chunk in enumerate(chunks):
            params = {"chat_id": chat_id, "text": chunk, "link_preview_options": {"is_disabled": True}}
            if parse_mode:
                params["parse_mode"] = parse_mode
            if kb is not None and i == len(chunks) - 1:
                params["reply_markup"] = kb
            try:
                last = await api.call("sendMessage", **params)
            except TelegramError as e:
                if e.blocked:
                    client = self.db.get_client_by_tg(tenant.slug, chat_id)
                    if client:
                        self.db.set_client_field(client["id"], "blocked", 1)
                    return None
                if parse_mode and "parse entities" in e.description:
                    params.pop("parse_mode", None)
                    params["text"] = strip_html(chunk)
                    try:
                        last = await api.call("sendMessage", **params)
                        continue
                    except (TelegramError, NetworkError):
                        pass
                log.warning("[%s] sendMessage %s: %s", tenant.name, chat_id, e)
                return None
            except NetworkError as e:
                log.warning("[%s] sendMessage %s: %s", tenant.name, chat_id, e)
                return None
        return last

    def main_kb(self, ctx: Ctx) -> dict:
        return reply_kb([[ctx.t("btn_book"), ctx.t("btn_my")], [ctx.t("btn_prices"), ctx.t("btn_contacts")]])

    def phone_kb(self, ctx: Ctx) -> dict:
        return reply_kb([[{"text": ctx.t("btn_share_phone"), "request_contact": True}], [ctx.t("btn_cancel")]],
                        one_time=True)

    @asynccontextmanager
    async def typing(self, ctx: Ctx):
        async def loop():
            while True:
                try:
                    await ctx.api.call("sendChatAction", _retries=0, chat_id=ctx.chat_id, action="typing")
                except (TelegramError, NetworkError):
                    pass
                await asyncio.sleep(4.5)

        task = asyncio.create_task(loop())
        await asyncio.sleep(0)  # дати індикатору «друкує…» стартувати одразу
        try:
            yield
        finally:
            task.cancel()

    def client_label(self, tenant: Tenant, row) -> str:
        keys = row.keys()
        name = (row["client_name"] if "client_name" in keys else row["name"] if "name" in keys else None) \
            or " ".join(p for p in (row["first_name"], row["last_name"]) if p) \
            or tenant.t(tenant.lang, "adm_client_noname")
        parts = [name]
        if row["username"]:
            parts.append(f"@{row['username']}")
        if row["phone"]:
            parts.append(row["phone"])
        return " · ".join(parts)

    async def notify_admins(self, tenant: Tenant, text: str, kb: dict | None = None,
                            client_id: int | None = None) -> None:
        for admin in tenant.admins:
            sent = await self.send(tenant, admin, text, kb)
            if sent and client_id is not None:
                self.db.add_relay(tenant.slug, admin, sent["message_id"], client_id, tenant.now())

    async def alert_tech(self, tenant: Tenant, error: str) -> None:
        now = tenant.now()
        last = self.last_alert.get(tenant.slug)
        if last and now - last < timedelta(hours=1):
            return
        self.last_alert[tenant.slug] = now
        for chat_id in tenant.tech_admins or tenant.admins:
            await self.send(tenant, chat_id, tenant.t(tenant.lang, "adm_ai_alert", name=tenant.name,
                                                      error=short(error, 300)))

    # ================================================================ повідомлення
    async def on_message(self, ctx: Ctx, msg: dict) -> None:
        text = (msg.get("text") or "").strip()
        tenant, db = ctx.tenant, ctx.db
        db.log_event(tenant.slug, ctx.client_id, "msg_in", tenant.now(), {"text": short(text or "[media]", 2000)})

        if text.startswith("/"):
            await self.on_command(ctx, text)
            return

        state = self.states.get(ctx.key)
        if state:
            kind, data = state
            if kind == "await_phone":
                if await self.state_await_phone(ctx, msg, data):
                    return
            elif kind == "admin_reply" and ctx.is_admin:
                await self.admin_relay(ctx, msg, data["client_id"])
                return

        if ctx.is_admin and msg.get("reply_to_message"):
            client_id = db.get_relay(tenant.slug, ctx.chat_id, msg["reply_to_message"].get("message_id"))
            if client_id:
                await self.admin_relay(ctx, msg, client_id)
                return

        if "contact" in msg:
            await self.save_contact(ctx, msg["contact"])
            return

        menu = self.menu_key(ctx, text)
        if menu is not None:
            self.pending.pop((tenant.slug, ctx.client_id), None)
            await self.run_menu(ctx, menu)
            return

        if text:
            await self.on_text(ctx, msg, text)
        elif any(k in msg for k in ("photo", "document", "video", "animation")):
            await self.on_media(ctx, msg)
        elif any(k in msg for k in ("voice", "video_note", "audio")):
            await ctx.send(ctx.t("voice_unsupported"))
        else:
            await ctx.send(ctx.t("unsupported"))

    def menu_key(self, ctx: Ctx, text: str) -> str | None:
        """Яку кнопку головного меню натиснуто (шукаємо підпис будь-якою мовою)."""
        if not text:
            return None
        for key in ("btn_book", "btn_my", "btn_prices", "btn_contacts"):
            if text in ctx.tenant.all_labels(key):
                return key
        return None

    async def run_menu(self, ctx: Ctx, key: str) -> None:
        if key == "btn_book":
            await self.flow_services(ctx, None)
        elif key == "btn_my":
            await self.show_my(ctx, None)
        elif key == "btn_prices":
            await self.show_prices(ctx)
        else:
            await self.show_contacts(ctx)

    async def on_command(self, ctx: Ctx, text: str) -> None:
        cmd, _, args = text.partition(" ")
        cmd = cmd.split("@", 1)[0].lower().lstrip("/")
        args = args.strip()
        if cmd in ("start", "help", "menu"):
            self.states.pop(ctx.key, None)
            await self.cmd_start(ctx)
        elif cmd == "cancel":
            self.states.pop(ctx.key, None)
            await ctx.send(ctx.t("state_cleared"), self.main_kb(ctx))
        elif cmd == "myid":
            await ctx.send(ctx.t("myid", id=ctx.user_id))
        elif ctx.is_admin and cmd in ADMIN_COMMANDS:
            await self.admin_command(ctx, cmd, args)
        else:
            await ctx.send(ctx.t("unknown_command"), self.main_kb(ctx))

    async def cmd_start(self, ctx: Ctx) -> None:
        ai = self.ai_status(ctx.tenant) in ("on", "paused")
        text = ctx.t("start" if ai else "start_no_ai", name=ctx.tenant.name)
        if ctx.is_admin:
            text += ctx.t("start_admin_hint")
        await ctx.send(text, self.main_kb(ctx))

    async def save_contact(self, ctx: Ctx, contact: dict) -> str | None:
        phone = normalize_phone(str(contact.get("phone_number") or ""), from_contact=True)
        if phone:
            ctx.db.set_client_field(ctx.client_id, "phone", phone)
            if contact.get("first_name") and contact.get("user_id") == ctx.user_id and not ctx.client["name"]:
                ctx.db.set_client_field(ctx.client_id, "name", short(contact["first_name"], 60))
            ctx.refresh()
            await ctx.send(ctx.t("phone_saved"), self.main_kb(ctx))
        else:
            await ctx.send(ctx.t("bad_phone"))
        return phone

    async def state_await_phone(self, ctx: Ctx, msg: dict, data: dict) -> bool:
        """Повертає True, якщо повідомлення оброблено в цьому стані."""
        text = (msg.get("text") or "").strip()
        if "contact" in msg:
            phone = await self.save_contact(ctx, msg["contact"])
            if not phone:
                return True
        elif text in ctx.tenant.all_labels("btn_cancel"):
            self.states.pop(ctx.key, None)
            await ctx.send(ctx.t("booking_aborted"), self.main_kb(ctx))
            return True
        elif self.menu_key(ctx, text) is not None:
            self.states.pop(ctx.key, None)
            return False
        else:
            phone = normalize_phone(text) if len(re.sub(r"\D", "", text)) >= 7 else None
            if not phone:
                await ctx.send(ctx.t("bad_phone"), self.phone_kb(ctx))
                return True
            ctx.db.set_client_field(ctx.client_id, "phone", phone)
            ctx.refresh()
            await ctx.send(ctx.t("phone_saved"), self.main_kb(ctx))
        self.states.pop(ctx.key, None)
        await self.dispatch(ctx, data["data"], None)
        return True

    # ---------------------------------------------------------------- AI
    def ai_status(self, tenant: Tenant) -> str:
        if self.agent is None:
            return "nokey"
        if not tenant.ai_enabled:
            return "disabled"
        if self.db.kv_get(tenant.slug, "paused") == "1":
            return "paused"
        return "on"

    def is_paused_for(self, ctx: Ctx) -> bool:
        if self.ai_status(ctx.tenant) == "paused":
            return True
        until = ctx.client["paused_until"]
        return bool(until) and parse_dt(until) > ctx.tenant.now()

    async def on_text(self, ctx: Ctx, msg: dict, text: str) -> None:
        tenant = ctx.tenant
        pending = self.pending.pop((tenant.slug, ctx.client_id), None)
        if pending and pending[1] > tenant.now() and is_affirmative(text):
            await self.dispatch(ctx, pending[0], pending[2])
            return
        if self.is_paused_for(ctx):
            await self.forward_to_admins(ctx, msg)
            return
        status = self.ai_status(tenant)
        if status != "on":
            await ctx.send(ctx.t("ai_off"), self.main_kb(ctx))
            return
        now = tenant.now()
        if (ctx.db.count_events(tenant.slug, "ai_message", now - timedelta(hours=1), ctx.client_id)
                >= tenant.ai_max_per_hour
                or ctx.db.count_events(tenant.slug, "ai_message", now - timedelta(days=1), ctx.client_id)
                >= tenant.ai_max_per_day):
            await ctx.send(ctx.t("rate_limited"), self.main_kb(ctx))
            return
        limit = tenant.ai_daily_token_limit if tenant.ai_daily_token_limit is not None \
            else self.settings.daily_token_limit
        if limit and ctx.db.tokens_since(tenant.slug, datetime.combine(now.date(), time.min)) >= limit:
            if ctx.db.kv_get(tenant.slug, "budget_alert") != now.date().isoformat():
                ctx.db.kv_set(tenant.slug, "budget_alert", now.date().isoformat())
                for chat_id in tenant.tech_admins or tenant.admins:
                    await self.send(tenant, chat_id, tenant.t(tenant.lang, "adm_budget_alert", name=tenant.name))
            await ctx.send(ctx.t("ai_off"), self.main_kb(ctx))
            return
        await self.run_ai(ctx, text)

    async def run_ai(self, ctx: Ctx, text: str) -> None:
        tenant = ctx.tenant
        ctx.db.log_event(tenant.slug, ctx.client_id, "ai_message", tenant.now())
        async with self.typing(ctx):
            result = await self.agent.reply(tenant, ctx.booking, ctx.db, ctx.client, short(text, 1500))
        if result.error:
            log.warning("[%s] AI: %s", tenant.name, result.error)
            ctx.db.log_event(tenant.slug, ctx.client_id, "ai_error", tenant.now(), {"error": short(result.error, 500)})
            await self.alert_tech(tenant, result.error)
        if result.refusal:
            await ctx.send(ctx.t("ai_refusal"))
            return
        if result.text:
            await ctx.send(result.text, parse_mode=None)
            ctx.db.log_event(tenant.slug, ctx.client_id, "msg_out", tenant.now(), {"text": short(result.text, 2000)})
        elif not result.effects:
            await ctx.send(ctx.t("ai_error"), self.main_kb(ctx))
        for effect in result.effects:
            kind = effect["type"]
            if kind == "confirm_booking":
                await self.send_ai_booking_card(ctx, effect)
            elif kind == "confirm_cancel":
                await self.send_cancel_card(ctx, effect["booking_id"], None, from_ai=True)
            elif kind == "confirm_reschedule":
                await self.send_reschedule_card(ctx, effect["booking_id"], effect["start"], effect["master_id"],
                                                None, from_ai=True)
            elif kind == "handoff":
                handed = await self.do_handoff(ctx, effect.get("reason") or "", effect.get("summary") or "")
                if not handed or not result.text:
                    await ctx.send(ctx.t("handoff_client") if handed else self.no_admin_text(ctx))

    def no_admin_text(self, ctx: Ctx) -> str:
        phone = ctx.tenant.info.get("phone")
        return ctx.t("handoff_no_admin", phone=f": {phone}" if phone else "")

    async def send_ai_booking_card(self, ctx: Ctx, effect: dict) -> None:
        tenant = ctx.tenant
        service = tenant.services.get(effect["service_id"])
        master = tenant.masters.get(effect["master_id"])
        if not service or not master:
            return
        start: datetime = effect["start"]
        data = f"ac:{service.id}:{master.id}:{start:%Y%m%d}:{start:%H%M}"
        text = ctx.t("card", service=service.title, master=master.name, day=tenant.day_label(start.date(), ctx.lang),
                     time=fmt_hhmm(start), duration=service.duration, price=tenant.price_str(service.price))
        kb = inline_kb([[ibtn(ctx.t("btn_confirm"), data)], [ibtn(ctx.t("btn_no_change"), "pn")]])
        sent = await ctx.send(text, kb)
        self.pending[(tenant.slug, ctx.client_id)] = (data, tenant.now() + PENDING_TTL,
                                                      sent["message_id"] if sent else None)

    async def on_media(self, ctx: Ctx, msg: dict) -> None:
        if self.is_paused_for(ctx):
            await self.forward_to_admins(ctx, msg)
            return
        handed = await self.do_handoff(ctx, ctx.at("adm_reason_media"), "")
        if not handed:
            await ctx.send(self.no_admin_text(ctx))
            return
        await self.forward_to_admins(ctx, msg, with_header=False)
        await ctx.send(ctx.t("media_received"))
        add_note(ctx.db, ctx.tenant, ctx.client_id, "Клієнт надіслав фото/файл; питання передано адміністратору.",
                 self.settings)

    # ---------------------------------------------------------------- передача людині
    async def do_handoff(self, ctx: Ctx, reason: str, summary: str) -> bool:
        tenant, db = ctx.tenant, ctx.db
        if not tenant.admins:
            return False
        now = tenant.now()
        hours = tenant.ai_handoff_hours
        db.set_client_field(ctx.client_id, "paused_until", dt_str(now + timedelta(hours=hours)))
        ctx.refresh()
        lines = []
        for role, text in history_transcript(db, ctx.client_id, now - timedelta(hours=self.settings.history_hours)):
            key = "adm_tr_client" if role == "user" else "adm_tr_bot"
            lines.append(ctx.at(key, text=short(text, 300)))
        message = ctx.at(
            "adm_handoff",
            client=self.client_label(tenant, ctx.client),
            reason=reason or "—",
            summary=Raw(ctx.at("adm_handoff_summary", summary=summary)) if summary else "",
            transcript=Raw("\n".join(lines) if lines else ctx.at("adm_tr_empty")),
            hours=hours,
        )
        kb = inline_kb([[ibtn(ctx.at("btn_adm_reply"), f"ar:{ctx.client_id}"),
                         ibtn(ctx.at("btn_adm_resume"), f"aR:{ctx.client_id}")]])
        await self.notify_admins(tenant, message, kb, client_id=ctx.client_id)
        db.log_event(tenant.slug, ctx.client_id, "handoff", now, {"reason": reason, "summary": summary})
        return True

    async def forward_to_admins(self, ctx: Ctx, msg: dict, with_header: bool = True) -> None:
        tenant = ctx.tenant
        label = self.client_label(tenant, ctx.client)
        kb = inline_kb([[ibtn(ctx.at("btn_adm_reply"), f"ar:{ctx.client_id}"),
                         ibtn(ctx.at("btn_adm_resume"), f"aR:{ctx.client_id}")]])
        text = (msg.get("text") or "").strip()
        for admin in tenant.admins:
            if text:
                sent = await self.send(tenant, admin, ctx.at("adm_client_msg", client=label, text=text), kb)
                if sent:
                    self.db.add_relay(tenant.slug, admin, sent["message_id"], ctx.client_id, tenant.now())
                continue
            if with_header:
                sent = await self.send(tenant, admin, ctx.at("adm_client_media", client=label), kb)
                if sent:
                    self.db.add_relay(tenant.slug, admin, sent["message_id"], ctx.client_id, tenant.now())
            try:
                copied = await ctx.api.call("copyMessage", chat_id=admin, from_chat_id=ctx.chat_id,
                                            message_id=msg["message_id"])
                self.db.add_relay(tenant.slug, admin, copied["message_id"], ctx.client_id, tenant.now())
            except (TelegramError, NetworkError) as e:
                log.warning("[%s] copyMessage: %s", tenant.name, e)
        if not tenant.admins:
            await ctx.send(self.no_admin_text(ctx))
        elif self.ai_status(tenant) == "paused":
            last = self.last_ack.get(ctx.key)
            if not last or tenant.now() - last > timedelta(hours=2):
                self.last_ack[ctx.key] = tenant.now()
                await ctx.send(ctx.t("paused_ack"))

    async def admin_relay(self, ctx: Ctx, msg: dict, client_id: int) -> None:
        tenant, db = ctx.tenant, ctx.db
        self.states.pop(ctx.key, None)
        client = db.get_client(client_id)
        if client is None or client["tenant"] != tenant.slug:
            await ctx.send(ctx.at("adm_reply_failed"))
            return
        text = (msg.get("text") or "").strip()
        lang = client["lang"] or tenant.lang
        title = tenant.info.get("admin_title") or tenant.t(lang, "admin_title")
        try:
            if text:
                await ctx.api.call("sendMessage", chat_id=client["tg_id"], parse_mode="HTML",
                                   text=tenant.t(lang, "admin_reply_to_client", title=title, text=text))
            else:
                await ctx.api.call("copyMessage", chat_id=client["tg_id"], from_chat_id=ctx.chat_id,
                                   message_id=msg["message_id"])
        except (TelegramError, NetworkError) as e:
            log.warning("[%s] Відповідь клієнту не доставлено: %s", tenant.name, e)
            await ctx.send(ctx.at("adm_reply_failed"))
            return
        now = tenant.now()
        db.set_client_field(client_id, "paused_until", dt_str(now + timedelta(hours=tenant.ai_handoff_hours)))
        add_note(db, tenant, client_id, f"Адміністратор написав клієнту: «{short(text or '[файл]', 300)}».",
                 self.settings)
        db.log_event(tenant.slug, client_id, "admin_reply", now)
        label = self.client_label(tenant, client)
        await ctx.send(ctx.at("adm_reply_sent", client=label),
                       inline_kb([[ibtn(ctx.at("btn_adm_resume"), f"aR:{client_id}")]]))

    # ================================================================ кнопки
    async def on_callback(self, ctx: Ctx, cq: dict) -> None:
        data = cq.get("data") or ""
        message_id = (cq.get("message") or {}).get("message_id")
        alert = None
        try:
            alert = await self.dispatch(ctx, data, message_id)
        except Expired:
            alert = ctx.t("alert_expired")
        except Exception:
            log.exception("Помилка обробки кнопки %s", data)
            alert = ctx.t("alert_expired")
        finally:
            try:
                await ctx.api.call("answerCallbackQuery", _retries=0, callback_query_id=cq["id"], text=alert)
            except (TelegramError, NetworkError):
                pass

    async def dispatch(self, ctx: Ctx, data: str, message_id: int | None) -> str | None:
        """Виконує дію кнопки. message_id=None — дія з тексту («так»): відповідь новим повідомленням."""
        parts = data.split(":")
        op, a = parts[0], parts[1:]
        if op.startswith("a") and op not in ("ac",):
            if not ctx.is_admin:
                return ctx.t("alert_no_access")
            return await self.admin_callback(ctx, op, a, message_id)
        if op == "menu":
            if a == ["book"]:
                await self.flow_services(ctx, message_id)
            elif a == ["my"]:
                await self.show_my(ctx, message_id)
            return None
        if op == "bs":
            if a:
                await self.flow_masters(ctx, a[0], message_id)
            else:
                await self.flow_services(ctx, message_id)
        elif op == "bm" and len(a) == 2:
            await self.flow_days(ctx, a[0], a[1], message_id)
        elif op == "bd" and len(a) == 3:
            await self.flow_times(ctx, a[0], a[1], _d(a[2]), message_id)
        elif op == "bt" and len(a) == 4:
            await self.flow_card(ctx, a[0], a[1], datetime.combine(_d(a[2]), _t(a[3])), message_id)
        elif op in ("bc", "ac") and len(a) == 4:
            await self.confirm_booking(ctx, op, a[0], a[1], datetime.combine(_d(a[2]), _t(a[3])), message_id)
        elif op in ("pn", "rn"):
            self.pending.pop((ctx.tenant.slug, ctx.client_id), None)
            await ctx.clear_kb(message_id)
            await ctx.send(ctx.t("proposal_declined"))
            add_note(ctx.db, ctx.tenant, ctx.client_id, "Клієнт відхилив запропонований варіант.", self.settings)
        elif op == "cx" and len(a) == 1:
            await self.send_cancel_card(ctx, _int(a[0]), message_id)
        elif op == "cy" and len(a) == 1:
            await self.do_cancel(ctx, _int(a[0]), message_id)
        elif op == "cn":
            self.pending.pop((ctx.tenant.slug, ctx.client_id), None)
            await ctx.show(message_id, ctx.t("cancel_kept"))
        elif op == "rd" and len(a) == 1:
            await self.resched_days(ctx, _int(a[0]), message_id)
        elif op == "rt" and len(a) == 2:
            await self.resched_times(ctx, _int(a[0]), _d(a[1]), message_id)
        elif op == "rk" and len(a) == 3:
            b = ctx.db.get_booking(_int(a[0]))
            master = b["master_id"] if b and b["master_id"] in ctx.tenant.masters else "any"
            start = datetime.combine(_d(a[1]), _t(a[2]))
            try:
                _, resolved = ctx.booking.validate_reschedule(_int(a[0]), start, master, ctx.client_id)
            except BookingError as e:
                await self.resched_error(ctx, e, _int(a[0]), start.date(), message_id)
                return None
            await self.send_reschedule_card(ctx, _int(a[0]), start, resolved, message_id)
        elif op == "ry" and len(a) == 4:
            await self.do_reschedule(ctx, _int(a[0]), datetime.combine(_d(a[1]), _t(a[2])), a[3], message_id)
        elif op == "ok" and len(a) == 1:
            await self.will_come(ctx, _int(a[0]), message_id)
        elif op == "nb" and len(a) == 2:
            master = a[1] if a[1] in ctx.tenant.masters else "any"
            await self.flow_days(ctx, a[0], master, message_id)
        elif op == "noff":
            ctx.db.set_client_field(ctx.client_id, "no_nudges", 1)
            await ctx.show(message_id, ctx.t("nudges_off"))
        else:
            raise Expired()
        return None

    # ---------------------------------------------------------------- запис кнопками
    def _service(self, ctx: Ctx, service_id: str):
        service = ctx.tenant.services.get(service_id)
        if service is None or not ctx.tenant.masters_for(service_id):
            raise Expired()
        return service

    def _master_label(self, ctx: Ctx, master_sel: str) -> str:
        if master_sel == "any":
            return ctx.t("any_master")
        master = ctx.tenant.masters.get(master_sel)
        if master is None:
            raise Expired()
        return master.name

    async def flow_services(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        rows = [[ibtn(ctx.t("btn_service", title=s.title, price=tenant.price_str(s.price)), f"bs:{s.id}")]
                for s in tenant.services.values() if tenant.masters_for(s.id)]
        await ctx.show(message_id, ctx.t("choose_service"), inline_kb(rows))

    async def flow_masters(self, ctx: Ctx, service_id: str, message_id: int | None) -> None:
        service = self._service(ctx, service_id)
        masters = ctx.tenant.masters_for(service_id)
        if len(masters) == 1:
            await self.flow_days(ctx, service_id, masters[0].id, message_id)
            return
        rows = _rows([ibtn(m.name, f"bm:{service_id}:{m.id}") for m in masters], 2)
        rows.append([ibtn(ctx.t("btn_any_master"), f"bm:{service_id}:any")])
        rows.append([ibtn(ctx.t("btn_back"), "bs")])
        await ctx.show(message_id, ctx.t("choose_master", service=service.title), inline_kb(rows))

    def _back_to_masters(self, ctx: Ctx, service_id: str) -> str:
        return "bs" if len(ctx.tenant.masters_for(service_id)) <= 1 else f"bs:{service_id}"

    async def flow_days(self, ctx: Ctx, service_id: str, master_sel: str, message_id: int | None,
                        prefix: str = "") -> None:
        service = self._service(ctx, service_id)
        master_label = self._master_label(ctx, master_sel)
        try:
            days = ctx.booking.available_days(service_id, master_sel)
        except BookingError:
            raise Expired() from None
        back = [ibtn(ctx.t("btn_back"), self._back_to_masters(ctx, service_id))]
        if not days:
            text = ctx.t("no_days", service=service.title, master=master_label, days=ctx.tenant.days_ahead)
            await ctx.show(message_id, text, inline_kb([back]))
            return
        buttons = [ibtn(ctx.tenant.day_button(d, ctx.lang), f"bd:{service_id}:{master_sel}:{d:%Y%m%d}") for d in days]
        text = (prefix + "\n\n" if prefix else "") + ctx.t("choose_day", service=service.title, master=master_label)
        await ctx.show(message_id, text, inline_kb(_rows(buttons, 3) + [back]))

    async def flow_times(self, ctx: Ctx, service_id: str, master_sel: str, day: date, message_id: int | None,
                         prefix: str = "") -> None:
        service = self._service(ctx, service_id)
        master_label = self._master_label(ctx, master_sel)
        try:
            slots = ctx.booking.free_slots(service_id, master_sel, day)
        except BookingError:
            raise Expired() from None
        day_label = ctx.tenant.day_label(day, ctx.lang)
        if not slots:
            await self.flow_days(ctx, service_id, master_sel, message_id,
                                 prefix=(prefix + "\n" if prefix else "") + ctx.t("no_times", day=day_label))
            return
        buttons = [ibtn(t, f"bt:{service_id}:{master_sel}:{day:%Y%m%d}:{t.replace(':', '')}") for t in slots]
        rows = _rows(buttons, 4) + [[ibtn(ctx.t("btn_back"), f"bm:{service_id}:{master_sel}")]]
        text = (prefix + "\n\n" if prefix else "") + ctx.t("choose_time", service=service.title, master=master_label,
                                                           day=day_label)
        await ctx.show(message_id, text, inline_kb(rows))

    async def flow_card(self, ctx: Ctx, service_id: str, master_sel: str, start: datetime,
                        message_id: int | None) -> None:
        tenant = ctx.tenant
        service = self._service(ctx, service_id)
        self._master_label(ctx, master_sel)
        try:
            resolved = ctx.booking.resolve_master(service_id, master_sel, start)
        except BookingError:
            raise Expired() from None
        if resolved is None:
            await self.flow_times(ctx, service_id, master_sel, start.date(), message_id, prefix=ctx.t("slot_taken"))
            return
        master = tenant.masters[resolved]
        text = ctx.t("card", service=service.title, master=master.name, day=tenant.day_label(start.date(), ctx.lang),
                     time=fmt_hhmm(start), duration=service.duration, price=tenant.price_str(service.price))
        kb = inline_kb([
            [ibtn(ctx.t("btn_confirm"), f"bc:{service_id}:{resolved}:{start:%Y%m%d}:{start:%H%M}")],
            [ibtn(ctx.t("btn_other_time"), f"bd:{service_id}:{master_sel}:{start:%Y%m%d}")],
        ])
        await ctx.show(message_id, text, kb)

    async def confirm_booking(self, ctx: Ctx, op: str, service_id: str, master_id: str, start: datetime,
                              message_id: int | None) -> None:
        tenant = ctx.tenant
        service = self._service(ctx, service_id)
        if master_id not in tenant.masters:
            raise Expired()
        key = (tenant.slug, ctx.client_id)
        if tenant.require_phone and not ctx.client["phone"]:
            self.states[ctx.key] = ("await_phone", {"data": f"{op}:{service_id}:{master_id}:{start:%Y%m%d}:{start:%H%M}"})
            self.pending.pop(key, None)
            await ctx.clear_kb(message_id)
            await ctx.send(ctx.t("ask_phone"), self.phone_kb(ctx))
            return
        source = "ai" if op == "ac" else "buttons"
        try:
            b = ctx.booking.create(ctx.client_id, service_id, master_id, start, source)
        except BookingError as e:
            self.pending.pop(key, None)
            if e.code == "duplicate":
                await ctx.show(message_id, ctx.t("already_booked"))
            elif e.code == "too_many":
                await ctx.show(message_id, ctx.t("too_many_active", count=e.info.get("count", 0)),
                               inline_kb([[ibtn(ctx.t("btn_my"), "menu:my")]]))
            elif e.code in ("slot_taken", "past", "too_soon", "too_far"):
                await self.flow_times(ctx, service_id, master_id, start.date(), message_id,
                                      prefix=ctx.t("slot_taken"))
            else:
                await ctx.show(message_id, ctx.t("booking_error"))
            return
        self.pending.pop(key, None)
        address = tenant.info.get("address")
        text = ctx.t("booked", service=b["service_title"], master=b["master_name"],
                     day=tenant.day_label(start.date(), ctx.lang), time=fmt_hhmm(start),
                     price=tenant.price_str(b["price"]),
                     address=Raw(ctx.t("booked_address", address=address)) if address else "")
        if message_id and await ctx.edit(message_id, text):
            pass
        else:
            await ctx.send(text, self.main_kb(ctx))
        add_note(ctx.db, tenant, ctx.client_id,
                 f"Клієнт підтвердив запис №{b['id']}: {b['service_title']}, {b['master_name']}, "
                 f"{start:%d.%m.%Y} о {fmt_hhmm(start)}.", self.settings)
        if tenant.notify_new_bookings:
            await self.notify_admins(tenant, ctx.at(
                "adm_new_booking", via=ctx.at("adm_via_ai") if source == "ai" else "",
                client=self.client_label(tenant, ctx.db.get_client(ctx.client_id)),
                service=b["service_title"], master=b["master_name"], day=tenant.day_label(start.date(), tenant.lang),
                time=fmt_hhmm(start), price=tenant.price_str(b["price"])), client_id=ctx.client_id)

    # ---------------------------------------------------------------- мої записи
    async def show_my(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        rows = ctx.booking.upcoming_for_client(ctx.client_id)
        if not rows:
            await ctx.show(message_id, ctx.t("my_none"), inline_kb([[ibtn(ctx.t("btn_book"), "menu:book")]]))
            return
        text = ctx.t("my_header")
        buttons = []
        for b in rows:
            start = parse_dt(b["start_at"])
            text += ctx.t("my_item", day=tenant.day_label(start.date(), ctx.lang), time=fmt_hhmm(start),
                          service=b["service_title"], master=b["master_name"])
            label = f"{start:%d.%m} {fmt_hhmm(start)}"
            buttons.append([ibtn(ctx.t("btn_resched_item", short=label), f"rd:{b['id']}"),
                            ibtn(ctx.t("btn_cancel_item", short=label), f"cx:{b['id']}")])
        await ctx.show(message_id, text, inline_kb(buttons))

    async def show_prices(self, ctx: Ctx) -> None:
        tenant = ctx.tenant
        text = ctx.t("prices_header")
        for s in tenant.services.values():
            masters = tenant.masters_for(s.id)
            if not masters:
                continue
            names = ", ".join(m.name for m in masters) if len(tenant.masters) > 1 else ""
            text += ctx.t("price_item", title=s.title, price=tenant.price_str(s.price), duration=s.duration,
                          masters=Raw(ctx.t("price_masters", masters=names)) if names else "")
            if s.description:
                text += ctx.t("price_desc", description=s.description)
        await ctx.send(text, inline_kb([[ibtn(ctx.t("btn_book"), "menu:book")]]))

    async def show_contacts(self, ctx: Ctx) -> None:
        tenant = ctx.tenant
        info = tenant.info
        text = ctx.t("contacts_header", name=tenant.name)
        if info.get("address"):
            text += ctx.t("contacts_address", address=info["address"])
        if info.get("phone"):
            text += ctx.t("contacts_phone", phone=info["phone"])
        text += ctx.t("contacts_hours", hours=info.get("hours") or tenant.schedule_summary(ctx.lang))
        if info.get("directions"):
            text += ctx.t("contacts_directions", directions=info["directions"])
        if info.get("payment"):
            text += ctx.t("contacts_payment", payment=info["payment"])
        rows = []
        if info.get("maps_url"):
            rows.append([url_btn(ctx.t("btn_map"), info["maps_url"])])
        rows.append([ibtn(ctx.t("btn_book"), "menu:book")])
        await ctx.send(text, inline_kb(rows))

    # ---------------------------------------------------------------- скасування
    def _booking_texts(self, ctx: Ctx, b) -> dict:
        start = parse_dt(b["start_at"])
        return {"service": b["service_title"], "master": b["master_name"],
                "day": ctx.tenant.day_label(start.date(), ctx.lang), "time": fmt_hhmm(start)}

    async def send_cancel_card(self, ctx: Ctx, booking_id: int, message_id: int | None, from_ai: bool = False) -> None:
        try:
            b = ctx.booking.validate_cancel(booking_id, ctx.client_id)
        except BookingError as e:
            await self.cancel_error(ctx, e, message_id)
            return
        kb = inline_kb([[ibtn(ctx.t("btn_yes_cancel"), f"cy:{b['id']}"), ibtn(ctx.t("btn_no"), "cn")]])
        shown = await ctx.show(message_id, ctx.t("cancel_ask", **self._booking_texts(ctx, b)), kb)
        if from_ai:
            self.pending[(ctx.tenant.slug, ctx.client_id)] = (f"cy:{b['id']}", ctx.tenant.now() + PENDING_TTL, shown)

    async def cancel_error(self, ctx: Ctx, e: BookingError, message_id: int | None) -> None:
        if e.code == "too_late":
            phone = ctx.tenant.info.get("phone")
            text = ctx.t("cancel_too_late", hours=e.info.get("hours", 0),
                         phone=Raw(ctx.t("cancel_too_late_phone", phone=phone)) if phone else "")
        else:
            text = ctx.t("booking_inactive")
        await ctx.show(message_id, text)

    async def do_cancel(self, ctx: Ctx, booking_id: int, message_id: int | None) -> None:
        tenant = ctx.tenant
        self.pending.pop((tenant.slug, ctx.client_id), None)
        try:
            b = ctx.booking.cancel(booking_id, "client", ctx.client_id)
        except BookingError as e:
            await self.cancel_error(ctx, e, message_id)
            return
        await ctx.show(message_id, ctx.t("cancelled"))
        start = parse_dt(b["start_at"])
        add_note(ctx.db, tenant, ctx.client_id, f"Запис №{b['id']} ({b['service_title']}, {start:%d.%m.%Y} о "
                                                f"{fmt_hhmm(start)}) скасовано клієнтом.", self.settings)
        await self.notify_admins(tenant, ctx.at(
            "adm_cancelled", client=self.client_label(tenant, ctx.client), service=b["service_title"],
            master=b["master_name"], day=tenant.day_label(start.date(), tenant.lang), time=fmt_hhmm(start)),
            client_id=ctx.client_id)

    # ---------------------------------------------------------------- перенесення
    def _resched_master(self, ctx: Ctx, b) -> str:
        return b["master_id"] if b["master_id"] in ctx.tenant.masters else "any"

    async def resched_days(self, ctx: Ctx, booking_id: int, message_id: int | None) -> None:
        try:
            b = ctx.booking.validate_cancel(booking_id, ctx.client_id)
        except BookingError as e:
            await self.cancel_error(ctx, e, message_id)
            return
        if b["service_id"] not in ctx.tenant.services:
            raise Expired()
        days = ctx.booking.available_days(b["service_id"], self._resched_master(ctx, b), exclude_id=b["id"])
        back = [ibtn(ctx.t("btn_back"), "menu:my")]
        if not days:
            await ctx.show(message_id, ctx.t("resched_none", days=ctx.tenant.days_ahead), inline_kb([back]))
            return
        buttons = [ibtn(ctx.tenant.day_button(d, ctx.lang), f"rt:{b['id']}:{d:%Y%m%d}") for d in days]
        await ctx.show(message_id, ctx.t("resched_choose_day", **self._booking_texts(ctx, b)),
                       inline_kb(_rows(buttons, 3) + [back]))

    async def resched_times(self, ctx: Ctx, booking_id: int, day: date, message_id: int | None,
                            prefix: str = "") -> None:
        try:
            b = ctx.booking.validate_cancel(booking_id, ctx.client_id)
        except BookingError as e:
            await self.cancel_error(ctx, e, message_id)
            return
        if b["service_id"] not in ctx.tenant.services:
            raise Expired()
        slots = ctx.booking.free_slots(b["service_id"], self._resched_master(ctx, b), day, exclude_id=b["id"])
        texts = self._booking_texts(ctx, b)
        if not slots:
            await self.resched_days(ctx, booking_id, message_id)
            return
        buttons = [ibtn(t, f"rk:{b['id']}:{day:%Y%m%d}:{t.replace(':', '')}") for t in slots]
        text = (prefix + "\n\n" if prefix else "") + ctx.t(
            "resched_choose_time", service=texts["service"], master=texts["master"],
            day=ctx.tenant.day_label(day, ctx.lang))
        await ctx.show(message_id, text, inline_kb(_rows(buttons, 4) + [[ibtn(ctx.t("btn_back"), f"rd:{b['id']}")]]))

    async def send_reschedule_card(self, ctx: Ctx, booking_id: int, start: datetime, master_id: str,
                                   message_id: int | None, from_ai: bool = False) -> None:
        tenant = ctx.tenant
        b = ctx.db.get_booking(booking_id)
        master = tenant.masters.get(master_id)
        if b is None or master is None:
            raise Expired()
        old_start = parse_dt(b["start_at"])
        old = f"{tenant.day_label(old_start.date(), ctx.lang)}, {fmt_hhmm(old_start)}"
        new = f"{tenant.day_label(start.date(), ctx.lang)}, {fmt_hhmm(start)}"
        if master_id != b["master_id"]:
            new += f" · {master.name}"
        data = f"ry:{b['id']}:{start:%Y%m%d}:{start:%H%M}:{master_id}"
        second = ibtn(ctx.t("btn_no_change"), "rn") if from_ai else \
            ibtn(ctx.t("btn_other_time"), f"rt:{b['id']}:{start:%Y%m%d}")
        kb = inline_kb([[ibtn(ctx.t("btn_confirm_resched"), data)], [second]])
        shown = await ctx.show(message_id, ctx.t("resched_card", service=b["service_title"], master=b["master_name"],
                                                 old=old, new=new), kb)
        if from_ai:
            self.pending[(tenant.slug, ctx.client_id)] = (data, tenant.now() + PENDING_TTL, shown)

    async def resched_error(self, ctx: Ctx, e: BookingError, booking_id: int, day: date,
                            message_id: int | None) -> None:
        if e.code in ("slot_taken", "past", "too_soon", "too_far"):
            await self.resched_times(ctx, booking_id, day, message_id, prefix=ctx.t("slot_taken"))
        elif e.code == "same_time":
            await ctx.show(message_id, ctx.t("already_booked"))
        else:
            await self.cancel_error(ctx, e, message_id)

    async def do_reschedule(self, ctx: Ctx, booking_id: int, start: datetime, master_id: str,
                            message_id: int | None) -> None:
        tenant = ctx.tenant
        self.pending.pop((tenant.slug, ctx.client_id), None)
        if master_id not in tenant.masters:
            raise Expired()
        try:
            old, new = ctx.booking.reschedule(booking_id, start, master_id, ctx.client_id)
        except BookingError as e:
            await self.resched_error(ctx, e, booking_id, start.date(), message_id)
            return
        await ctx.show(message_id, ctx.t("rescheduled", service=new["service_title"], master=new["master_name"],
                                         day=tenant.day_label(start.date(), ctx.lang), time=fmt_hhmm(start)))
        old_start = parse_dt(old["start_at"])
        add_note(ctx.db, tenant, ctx.client_id, f"Запис №{new['id']} перенесено на {start:%d.%m.%Y} о "
                                                f"{fmt_hhmm(start)} ({new['master_name']}).", self.settings)
        await self.notify_admins(tenant, ctx.at(
            "adm_rescheduled", client=self.client_label(tenant, ctx.client), service=new["service_title"],
            master=new["master_name"],
            old=f"{tenant.day_label(old_start.date(), tenant.lang)}, {fmt_hhmm(old_start)} ({old['master_name']})",
            new=f"{tenant.day_label(start.date(), tenant.lang)}, {fmt_hhmm(start)}"), client_id=ctx.client_id)

    # ---------------------------------------------------------------- нагадування
    def reminder_text(self, tenant: Tenant, b, lang: str, confirmed: bool = False) -> str:
        start = parse_dt(b["start_at"])
        address = tenant.info.get("address")
        text = tenant.t(lang, "reminder", day=tenant.day_label(start.date(), lang), time=fmt_hhmm(start),
                        service=b["service_title"], master=b["master_name"],
                        address=Raw(tenant.t(lang, "booked_address", address=address)) if address else "")
        if confirmed:
            text += tenant.t(lang, "will_come_ok")
        return text

    def reminder_kb(self, tenant: Tenant, b, lang: str) -> dict:
        return inline_kb([
            [ibtn(tenant.t(lang, "btn_will_come"), f"ok:{b['id']}")],
            [ibtn(tenant.t(lang, "btn_resched"), f"rd:{b['id']}"),
             ibtn(tenant.t(lang, "btn_cancel_booking"), f"cx:{b['id']}")],
        ])

    async def will_come(self, ctx: Ctx, booking_id: int, message_id: int | None) -> None:
        b = ctx.db.get_booking(booking_id)
        if b is None or b["client_id"] != ctx.client_id or b["status"] != "active":
            await ctx.show(message_id, ctx.t("booking_inactive"))
            return
        if not b["client_confirmed"]:
            ctx.db.set_booking_field(booking_id, "client_confirmed", 1)
            ctx.db.log_event(ctx.tenant.slug, ctx.client_id, "reminder_confirmed", ctx.tenant.now(), {"id": booking_id})
        await ctx.show(message_id, self.reminder_text(ctx.tenant, b, ctx.lang, confirmed=True))

    # ================================================================ адмін
    async def admin_command(self, ctx: Ctx, cmd: str, args: str) -> None:
        tenant = ctx.tenant
        today = tenant.today()
        if cmd == "start":
            await self.cmd_start(ctx)
        elif cmd == "admin":
            await ctx.send(ctx.at("admin_help", name=tenant.name, ai_status=ctx.at(f"ai_status_{self.ai_status(tenant)}")))
        elif cmd in ("today", "tomorrow"):
            await self.admin_day(ctx, today if cmd == "today" else today + timedelta(days=1), None)
        elif cmd == "week":
            await ctx.send(self.render_week(tenant, today))
        elif cmd == "all":
            await ctx.send(self.render_upcoming(tenant, today))
        elif cmd == "stats":
            await ctx.send(ctx.at("adm_stats", **compute_stats(ctx.db, tenant, self.settings)))
        elif cmd == "block":
            await self.admin_block(ctx, args)
        elif cmd == "blocks":
            await self.admin_blocks(ctx, None)
        elif cmd == "pause":
            ctx.db.kv_set(tenant.slug, "paused", "1")
            await ctx.send(ctx.at("adm_paused"))
        elif cmd == "resume":
            ctx.db.kv_set(tenant.slug, "paused", "0")
            await ctx.send(ctx.at("adm_resumed_all"))
        elif cmd == "reload":
            await self.admin_reload(ctx)
        elif cmd == "myid":
            await ctx.send(ctx.t("myid", id=ctx.user_id))

    def render_day(self, tenant: Tenant, day: date, rows) -> str:
        lang = tenant.lang
        label = tenant.day_label(day, lang)
        if not rows:
            return tenant.t(lang, "adm_day_empty", day=label)
        active = [r for r in rows if r["status"] == "active"]
        text = tenant.t(lang, "adm_day_header", day=label, count=len(active))
        for r in rows:
            flags = ""
            if r["client_confirmed"]:
                flags += " ✅"
            if r["source"] == "ai":
                flags += " 🤖"
            if r["status"] == "no_show":
                flags += " 🚫"
            text += tenant.t(lang, "adm_booking_line", start=r["start_at"][11:16], end=r["end_at"][11:16],
                             master=r["master_name"], service=r["service_title"],
                             client=self.client_label(tenant, r), flags=flags, id=r["id"])
        return text

    async def admin_day(self, ctx: Ctx, day: date, message_id: int | None) -> None:
        rows = ctx.booking.day_bookings(day)
        text = self.render_day(ctx.tenant, day, rows)
        buttons = [[ibtn(f"🚫 #{r['id']}", f"ans:{r['id']}"), ibtn(f"🗑 #{r['id']}", f"acx:{r['id']}")]
                   for r in rows if r["status"] == "active"]
        if buttons:
            text += ctx.at("adm_legend")
        await ctx.show(message_id, text, inline_kb(buttons) if buttons else None)

    def _active_from(self, tenant: Tenant, start_day: date, days: int | None = None,
                     statuses: tuple[str, ...] = ("active",)):
        """Записи від початку start_day: на days днів або всі майбутні."""
        start = datetime.combine(start_day, time.min)
        end = start + timedelta(days=days if days is not None else 3650)
        return self.db.bookings_between(tenant.slug, start, end, statuses)

    def _render_by_day(self, tenant: Tenant, header: str, rows) -> str:
        lang = tenant.lang
        text = tenant.t(lang, header)
        by_day: dict[str, list] = {}
        for r in rows:
            by_day.setdefault(r["start_at"][:10], []).append(r)
        for day_str, day_rows in by_day.items():
            day = date.fromisoformat(day_str)
            active = sum(1 for r in day_rows if r["status"] == "active")
            text += tenant.t(lang, "adm_week_day", day=tenant.day_label(day, lang), count=active)
            if active < len(day_rows):
                text += tenant.t(lang, "adm_day_cancelled", count=len(day_rows) - active)
            for r in day_rows:
                text += tenant.t(lang, "adm_week_line", start=r["start_at"][11:16], master=r["master_name"],
                                 service=r["service_title"], client=self.client_label(tenant, r))
                if r["status"] == "cancelled":
                    by = "admin" if r["cancelled_by"] == "admin" else "client"
                    text += tenant.t(lang, f"adm_cancelled_by_{by}")
        if not rows:
            text += tenant.t(lang, "adm_week_empty")
        return text

    def render_week(self, tenant: Tenant, start_day: date) -> str:
        text = self._render_by_day(tenant, "adm_week_header", self._active_from(tenant, start_day, 7))
        # Клієнти можуть записуватися далі ніж на тиждень (days_ahead) — не ховаємо ці записи мовчки.
        later = len(self._active_from(tenant, start_day + timedelta(days=7)))
        if later:
            text += tenant.t(tenant.lang, "adm_week_more", count=later)
        return text

    def render_upcoming(self, tenant: Tenant, start_day: date) -> str:
        rows = self._active_from(tenant, start_day, statuses=("active", "cancelled"))
        return self._render_by_day(tenant, "adm_all_header", rows)

    def _block_usage(self, tenant: Tenant) -> str:
        example = next(iter(tenant.masters))
        masters = ", ".join(f"{m.id} ({m.name})" for m in tenant.masters.values())
        return tenant.t(tenant.lang, "adm_block_usage", example=example, masters=masters)

    async def admin_block(self, ctx: Ctx, args: str) -> None:
        tenant = ctx.tenant
        usage = self._block_usage(tenant)
        parts = args.split()
        if len(parts) < 2:
            await ctx.send(usage)
            return
        who = parts[0].lower()
        if who in ("all", "*", "всі", "все"):
            master_id = None
        elif who in tenant.masters:
            master_id = who
        else:
            matches = [m.id for m in tenant.masters.values() if m.name.lower() == who]
            master_id = matches[0] if matches else ""
        day = parse_user_date(parts[1], tenant.today())
        if master_id == "" or day is None:
            await ctx.send(ctx.at("adm_block_bad", usage=Raw(usage)))
            return
        rest = parts[2:]
        if rest and RANGE_RE.match(rest[0]):
            m = RANGE_RE.match(rest[0])
            try:
                t1 = parse_hhmm(f"{m.group(1)}:{m.group(2)}")
                t2 = parse_hhmm(f"{m.group(3)}:{m.group(4)}")
            except ValueError:
                await ctx.send(ctx.at("adm_block_bad", usage=Raw(usage)))
                return
            if t2 <= t1:
                await ctx.send(ctx.at("adm_block_bad", usage=Raw(usage)))
                return
            start, end = datetime.combine(day, t1), datetime.combine(day, t2)
            range_text = f"{fmt_hhmm(t1)}–{fmt_hhmm(t2)}"
            note = " ".join(rest[1:])
        else:
            start = datetime.combine(day, time.min)
            end = start + timedelta(days=1)
            range_text = ctx.at("adm_whole_day")
            note = " ".join(rest)
        _, conflicts = ctx.booking.add_block(master_id, start, end, short(note, 100))
        master_name = tenant.masters[master_id].name if master_id else ctx.at("adm_all_masters")
        text = ctx.at("adm_block_done", master=master_name, day=tenant.day_label(day, tenant.lang), range=range_text,
                      note=f" — {note}" if note else "")
        if conflicts:
            lines = []
            for b in conflicts:
                client = ctx.db.get_client(b["client_id"])
                lines.append(f"\n• {b['start_at'][11:16]} {b['master_name']} · {self.client_label(tenant, client)}"
                             f" · #{b['id']}")
            text += ctx.at("adm_block_conflicts", lines="".join(lines))
        await ctx.send(text)

    async def admin_blocks(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        rows = ctx.db.future_blocks(tenant.slug, tenant.now())
        if not rows:
            await ctx.show(message_id, ctx.at("adm_blocks_empty"))
            return
        buttons = []
        for bl in rows[:40]:
            start, end = parse_dt(bl["start_at"]), parse_dt(bl["end_at"])
            whole = start.time() == time.min and end - start >= timedelta(days=1)
            rng = ctx.at("adm_whole_day") if whole else f"{fmt_hhmm(start)}–{fmt_hhmm(end)}"
            master = tenant.masters[bl["master_id"]].name if bl["master_id"] in tenant.masters else \
                ctx.at("adm_all_masters")
            label = ctx.at("btn_adm_block_item", master=master, day=f"{start:%d.%m}", range=rng)
            buttons.append([ibtn(short(label, 60), f"abd:{bl['id']}")])
        await ctx.show(message_id, ctx.at("adm_blocks_header"), inline_kb(buttons))

    async def admin_reload(self, ctx: Ctx) -> None:
        slug = ctx.tenant.slug
        old = self.tenants[slug]
        try:
            new = load_tenant(old.path)
        except ConfigError as e:
            await ctx.send(ctx.at("adm_reload_failed", error=str(e)))
            return
        token_changed = new.bot_token != old.bot_token
        new.bot_token = old.bot_token
        self.tenants[slug] = new
        self.bookings[slug] = BookingService(new, self.db)
        text = new.t(new.lang, "adm_reloaded", services=len(new.services), masters=len(new.masters))
        if token_changed:
            text += new.t(new.lang, "adm_reload_token")
        await self.send(new, ctx.chat_id, text)

    async def admin_callback(self, ctx: Ctx, op: str, a: list[str], message_id: int | None) -> str | None:
        tenant = ctx.tenant
        if op == "ar" and len(a) == 1:
            client = ctx.db.get_client(_int(a[0]))
            if client is None or client["tenant"] != tenant.slug:
                raise Expired()
            self.states[ctx.key] = ("admin_reply", {"client_id": client["id"]})
            await ctx.send(ctx.at("adm_reply_prompt", client=self.client_label(tenant, client)))
        elif op == "aR" and len(a) == 1:
            client = ctx.db.get_client(_int(a[0]))
            if client is None or client["tenant"] != tenant.slug:
                raise Expired()
            ctx.db.set_client_field(client["id"], "paused_until", None)
            if self.states.get(ctx.key, ("", {}))[1].get("client_id") == client["id"]:
                self.states.pop(ctx.key, None)
            await ctx.clear_kb(message_id)
            await ctx.send(ctx.at("adm_resumed", client=self.client_label(tenant, client)))
        elif op == "ans" and len(a) == 1:
            try:
                b = ctx.booking.mark_no_show(_int(a[0]))
            except BookingError:
                raise Expired() from None
            await self.admin_day(ctx, parse_dt(b["start_at"]).date(), message_id)
            return ctx.at("adm_noshow_done", id=b["id"])
        elif op == "acx" and len(a) == 1:
            b = ctx.db.get_booking(_int(a[0]))
            if b is None or b["tenant"] != tenant.slug or b["status"] != "active":
                raise Expired()
            client = ctx.db.get_client(b["client_id"])
            line = (f"{b['start_at'][8:10]}.{b['start_at'][5:7]} {b['start_at'][11:16]} · {b['master_name']} · "
                    f"{b['service_title']} · {self.client_label(tenant, client)}")
            kb = inline_kb([[ibtn(ctx.at("btn_adm_yes_cancel"), f"acy:{b['id']}"), ibtn(ctx.at("btn_no"), "ax")]])
            await ctx.send(ctx.at("adm_cancel_ask", id=b["id"], line=line), kb)
        elif op == "acy" and len(a) == 1:
            try:
                b = ctx.booking.cancel(_int(a[0]), "admin")
            except BookingError:
                raise Expired() from None
            await ctx.show(message_id, ctx.at("adm_cancelled_done", id=b["id"]))
            client = ctx.db.get_client(b["client_id"])
            if client and not client["blocked"]:
                lang = client["lang"] or tenant.lang
                start = parse_dt(b["start_at"])
                await self.send(tenant, client["tg_id"], tenant.t(
                    lang, "client_cancelled_by_admin", service=b["service_title"], master=b["master_name"],
                    day=tenant.day_label(start.date(), lang), time=fmt_hhmm(start)))
                add_note(ctx.db, tenant, client["id"], f"Адміністратор скасував запис №{b['id']}.", self.settings)
        elif op == "abd" and len(a) == 1:
            ctx.db.delete_block(tenant.slug, _int(a[0]))
            await self.admin_blocks(ctx, message_id)
            return ctx.at("adm_block_deleted")
        elif op == "ax":
            await ctx.clear_kb(message_id)
        else:
            raise Expired()
        return None
