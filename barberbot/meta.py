"""Instagram Direct і Facebook Messenger через Meta Graph API.

Бот і далі «говорить» мовою Telegram Bot API. MetaRouter приймає ті самі виклики (sendMessage,
editMessageText, answerCallbackQuery…) і для клієнтів з Instagram чи Messenger перекладає їх у Send API Meta;
усе інше передає справжньому Telegram. MetaGateway робить навпаки: події з вебхука Meta перетворює
на оновлення у форматі Telegram. Тому запис, AI, нагадування й адмінка працюють для всіх каналів однаково.

Клієнт з Meta отримує в базі «telegram id» з окремого діапазону (IG_BASE, FB_BASE) — його не сплутати
з користувачем Telegram, а записи й розклад закладу спільні для всіх каналів.
Адміністратори й майстри, як і раніше, працюють у Telegram.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import html
import itertools
import json
import logging
import re
import urllib.parse
from collections import OrderedDict

from .telegram import NET_ERRORS, POOL, NetworkError, TelegramError, run_blocking
from .texts import TEXTS

log = logging.getLogger("barberbot.meta")

IG_BASE = 1 << 53  # Instagram: id клієнтів від 2^53 (id Telegram — менші)
FB_BASE = 1 << 54  # Messenger: від 2^54
PLATFORM_LABEL = {"instagram": "📷 Instagram", "messenger": "💬 Messenger"}
TEXT_LIMIT = {"instagram": 1000, "messenger": 2000}  # максимальна довжина одного повідомлення
QR_MAX = 13       # швидких відповідей під повідомленням
QR_PAGE = 11      # на сторінку, коли варіантів більше за QR_MAX (+ «◀️» і «▶️»)
TITLE_MAX = 20    # символів у підписі швидкої відповіді
LANG_TITLES = {"uk": "🇺🇦 Українська", "ru": "Русский", "en": "🇬🇧 English", "hu": "🇭🇺 Magyar", "de": "🇩🇪 Deutsch"}
# Мітки (message tags) для повідомлень поза 24-годинним вікном Meta.
EVENT_TAGS = {"messenger": "CONFIRMED_EVENT_UPDATE"}           # нагадування й зміни запису
HUMAN_TAGS = {"messenger": "HUMAN_AGENT", "instagram": "HUMAN_AGENT"}  # відповідь адміністратора


def platform_of(chat_id) -> str | None:
    if not isinstance(chat_id, int):
        return None
    if IG_BASE <= chat_id < FB_BASE:
        return "instagram"
    if FB_BASE <= chat_id < FB_BASE + (1 << 54):
        return "messenger"
    return None


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def qr_title(label: str) -> str:
    """Підпис кнопки меню в межах 20 символів Meta: спершу без смайлика на початку, далі — обрізаний по слову."""
    if utf16_len(label) <= TITLE_MAX:
        return label
    head, _, rest = label.partition(" ")
    if rest and not any(ch.isalnum() for ch in head):
        label = rest
    if utf16_len(label) <= TITLE_MAX:
        return label
    cut = label[:TITLE_MAX - 1]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,&-") + "…"


def html_to_text(text: str) -> str:
    """Розмітка Telegram (<b>, <i>, <code>) → звичайний текст: Instagram і Messenger HTML не підтримують."""
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def split_text(text: str, limit: int) -> list[str]:
    """Ділить текст на частини не довші за limit — по рядках, а задовгі рядки — по словах."""
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            cut = line.rfind(" ", 0, limit)
            cut = cut if cut > limit // 2 else limit
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:cut])
            line = line[cut:].lstrip()
        candidate = f"{cur}\n{line}" if cur else line
        if len(candidate) > limit:
            parts.append(cur)
            cur = line
        else:
            cur = candidate
    if cur or not parts:
        parts.append(cur)
    return [p for p in parts if p.strip()] or [text[:limit]]


class MetaError(Exception):
    def __init__(self, code: int, subcode: int, message: str):
        super().__init__(message)
        self.code, self.subcode, self.message = code, subcode, message

    @property
    def outside_window(self) -> bool:
        """Минуло понад 24 години від останнього повідомлення клієнта — без мітки писати не можна."""
        return self.subcode in (2018278, 2534022) or (self.code == 10 and "window" in self.message.lower())

    @property
    def unavailable(self) -> bool:
        """Клієнт видалив акаунт, заблокував сторінку чи вимкнув повідомлення."""
        return self.code == 551 or self.subcode in (1545041, 2018108)


# ================================================================ Graph API одного закладу

class MetaChannel:
    """Сторінка Facebook закладу (і прив'язаний Instagram): надсилання повідомлень і зв'язок id клієнтів."""

    def __init__(self, tenant, settings, db, transport=None):
        self.slug = tenant.slug
        self.tenant = tenant
        self.page_id = tenant.meta_page_id
        self.ig_id = tenant.meta_instagram_id
        self.token = tenant.meta_page_token
        self.base = f"{settings.meta_graph_base}/{settings.meta_graph_version}"
        self.db = db
        # transport(method, url, body) -> (статус, тіло); у тестах — підробка.
        self.transport = transport or self._http

    # ---- id клієнтів: (платформа, id у Meta) ↔ «telegram id» у базі
    def chat_id(self, platform: str, psid: str) -> int:
        key = f"meta:{platform}:{psid}"
        known = self.db.kv_get(self.slug, key)
        if known:
            return int(known)
        counter = f"meta:next:{platform}"
        n = int(self.db.kv_get(self.slug, counter) or 0) + 1
        self.db.kv_set(self.slug, counter, str(n))
        chat = (IG_BASE if platform == "instagram" else FB_BASE) + n
        self.db.kv_set(self.slug, key, str(chat))
        self.save_user(chat, {"platform": platform, "psid": psid})
        return chat

    def user(self, chat_id: int) -> dict:
        raw = self.db.kv_get(self.slug, f"meta:id:{chat_id}")
        return json.loads(raw) if raw else {}

    def save_user(self, chat_id: int, data: dict) -> None:
        self.db.kv_set(self.slug, f"meta:id:{chat_id}", json.dumps(data, ensure_ascii=False))

    # ---- Graph API
    @staticmethod
    def _http(method: str, url: str, body: bytes | None) -> tuple[int, bytes]:
        headers = {"Content-Type": "application/json"} if body is not None else {}
        status, raw, _ = POOL.request(method, url, body, headers, 20)
        return status, raw

    def _call_sync(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        query = urllib.parse.urlencode({**(params or {}), "access_token": self.token})
        url = f"{self.base}/{path}?{query}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        try:
            status, raw = self.transport(method, url, data)
        except NET_ERRORS as e:
            raise NetworkError(str(e) or e.__class__.__name__) from None
        try:
            result = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            raise MetaError(status, 0, f"HTTP {status}") from None
        if status >= 400 or "error" in result:
            err = result.get("error") or {}
            raise MetaError(int(err.get("code") or status), int(err.get("error_subcode") or 0),
                            str(err.get("message") or f"HTTP {status}"))
        return result

    async def graph(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        return await run_blocking(self._call_sync, method, path, params, body)

    async def send(self, chat_id: int, message: dict | None = None, tag: str | None = None,
                   action: str | None = None) -> dict:
        user = self.user(chat_id)
        platform, psid = user.get("platform"), user.get("psid")
        if not psid:
            raise MetaError(551, 0, "unknown Meta user")
        body: dict = {"recipient": {"id": psid}}
        if action:
            body["sender_action"] = action
        else:
            body["messaging_type"] = "RESPONSE"
            body["message"] = message
        try:
            return await self.graph("POST", f"{self.page_id}/messages", body=body)
        except MetaError as e:
            meta_tag = (EVENT_TAGS if tag == "event" else HUMAN_TAGS if tag == "human" else {}).get(platform)
            if not (e.outside_window and meta_tag and not action):
                raise
            body.update(messaging_type="MESSAGE_TAG", tag=meta_tag)
            return await self.graph("POST", f"{self.page_id}/messages", body=body)

    async def fetch_profile(self, platform: str, psid: str) -> dict:
        fields = "name,username" if platform == "instagram" else "first_name,last_name"
        try:
            data = await asyncio.wait_for(self.graph("GET", psid, {"fields": fields}), 8)
        except (MetaError, NetworkError, asyncio.TimeoutError) as e:
            log.info("[%s] Профіль %s %s: %s", self.tenant.name, platform, psid, e)
            return {}
        if platform == "instagram":
            return {"first_name": data.get("name") or data.get("username"), "username": data.get("username")}
        return {"first_name": data.get("first_name"), "last_name": data.get("last_name")}

    async def check(self) -> str:
        """Для `run.py check`: назва сторінки або виняток."""
        data = await self.graph("GET", self.page_id, {"fields": "name"})
        return data.get("name") or self.page_id


# ================================================================ Telegram-подібний API

class MetaRouter:
    """Той самий інтерфейс, що й TelegramAPI. Чати з Meta — через MetaChannel, решта — у Telegram."""

    def __init__(self, tg, channel: MetaChannel):
        self.tg = tg
        self.channel = channel
        self.tenant = channel.tenant
        self._ids = itertools.count(1)
        self.media: OrderedDict[tuple[int, int], dict] = OrderedDict()  # (чат, id повідомлення) → вкладення
        self.callbacks: OrderedDict[str, int] = OrderedDict()           # id натискання → чат
        self.pages: dict[int, dict] = {}                                # чат → кнопки, що не вмістилися

    def next_id(self) -> int:
        return next(self._ids)

    @staticmethod
    def _remember(store: OrderedDict, key, value, limit: int = 500) -> None:
        store[key] = value
        while len(store) > limit:
            store.popitem(last=False)

    def remember_media(self, chat_id: int, message_id: int, attachment: dict) -> None:
        self._remember(self.media, (chat_id, message_id), attachment)

    def remember_callback(self, cq_id: str, chat_id: int) -> None:
        self._remember(self.callbacks, cq_id, chat_id)

    async def send_document(self, chat_id: int, *args, **kwargs):
        if platform_of(chat_id):
            raise TelegramError(400, "Bad Request: files can't be sent to Instagram/Messenger")
        return await self.tg.send_document(chat_id, *args, **kwargs)

    async def call(self, method: str, _timeout: float = 30, _retries: int = 2, **params):
        tag = params.pop("_meta_tag", None)
        if method == "answerCallbackQuery" and str(params.get("callback_query_id", "")).startswith("meta:"):
            chat = self.callbacks.get(params["callback_query_id"])
            if chat and params.get("text"):
                await self._guard(self.send_text(chat, params["text"], None, None, None))
            return True
        if method == "copyMessage" and platform_of(params.get("from_chat_id")):
            return await self._copy_from_meta(params)
        chat = params.get("chat_id")
        if not platform_of(chat):
            return await self.tg.call(method, _timeout, _retries, **params)
        if method == "sendMessage":
            return await self._guard(self.send_text(chat, params.get("text") or "", params.get("parse_mode"),
                                                    params.get("reply_markup"), tag))
        if method == "sendChatAction":
            try:
                await self.channel.send(chat, action="typing_on")
            except (MetaError, NetworkError):
                pass
            return True
        if method in ("editMessageText", "editMessageCaption"):
            raise TelegramError(400, "Bad Request: message can't be edited")
        if method in ("editMessageReplyMarkup", "deleteMessage", "setMyCommands", "deleteMyCommands"):
            return True
        raise TelegramError(400, f"Bad Request: {method} is not supported in Instagram/Messenger")

    async def _guard(self, coro):
        """Помилки Meta → помилки у форматі Telegram, які бот уже вміє обробляти."""
        try:
            return await coro
        except MetaError as e:
            if e.unavailable:
                raise TelegramError(403, f"Forbidden: {e.message}") from None
            raise TelegramError(400, f"Bad Request: {e.message}") from None

    # ---- надсилання тексту з кнопками
    def main_menu(self, chat: int) -> dict:
        """Головне меню клієнта. У Telegram воно завжди під полем вводу, а в Meta швидкі відповіді зникають
        після кожного повідомлення — тож додаємо його до кожного повідомлення без власних кнопок."""
        texts = TEXTS.get(self.channel.user(chat).get("lang") or self.tenant.lang, TEXTS["en"])
        return {"keyboard": [[{"text": texts["btn_book"]}, {"text": texts["btn_my"]}],
                             [{"text": texts["btn_prices"]}, {"text": texts["btn_contacts"]}]],
                "is_persistent": True}

    def _options(self, chat: int, kb: dict | None) -> tuple[list[tuple[str, str]], list[str], bool]:
        """Кнопки Telegram → [(підпис, payload)], рядки з посиланнями, чи це головне меню."""
        if not kb or not (kb.get("inline_keyboard") or kb.get("keyboard")):
            kb = self.main_menu(chat)
        platform = platform_of(chat)
        options, links = [], []
        for row in kb.get("inline_keyboard") or []:
            for b in row:
                if b.get("url"):
                    links.append(f"🔗 {b['text']}: {b['url']}")
                elif b.get("callback_data"):
                    options.append((b["text"], f"cb:{b['callback_data']}"))
        for row in kb.get("keyboard") or []:
            for b in row:
                b = b if isinstance(b, dict) else {"text": b}
                if b.get("request_contact"):
                    if platform == "messenger":
                        options.append(("", "phone"))  # Messenger підставить номер клієнта
                    continue
                options.append((b["text"], f"txt:{b['text']}"))
        main_menu = bool(kb.get("keyboard")) and kb.get("is_persistent", False)
        if main_menu and len(self.tenant.languages) > 1:
            lang = self.channel.user(chat).get("lang") or self.tenant.lang
            options.append((TEXTS.get(lang, TEXTS["en"])["btn_language"], "lang:?"))
        return options, links, main_menu

    @staticmethod
    def _quick_replies(options: list[tuple[str, str]], numbered: bool, page: int) -> list[dict]:
        total = len(options)
        if total <= QR_MAX:
            start, end = 0, total
        else:
            start, end = page * QR_PAGE, min(total, (page + 1) * QR_PAGE)
        replies = []
        if start > 0:
            replies.append({"content_type": "text", "title": "◀️", "payload": f"pg:{page - 1}"})
        for i in range(start, end):
            title, payload = options[i]
            if payload == "phone":
                replies.append({"content_type": "user_phone_number"})
            else:
                label = str(i + 1) if numbered else qr_title(title)
                replies.append({"content_type": "text", "title": label, "payload": payload})
        if end < total:
            replies.append({"content_type": "text", "title": "▶️", "payload": f"pg:{page + 1}"})
        return replies

    async def send_text(self, chat: int, text: str, parse_mode: str | None, kb: dict | None,
                        tag: str | None) -> dict:
        platform = platform_of(chat)
        if parse_mode == "HTML":
            text = html_to_text(text)
        options, links, _ = self._options(chat, kb)
        url_buttons = [b for row in (kb or {}).get("inline_keyboard") or [] for b in row if b.get("url")]
        if url_buttons and not options and len(text.strip()) <= 640:
            # Лише кнопки-посилання (онлайн-запис, карта) — справжні кнопки шаблону Meta, що відкривають сторінку
            # у вікні всередині Messenger. Якщо платформа шаблон не прийме — нижче надішлемо посиланнями в тексті.
            message = {"attachment": {"type": "template", "payload": {
                "template_type": "button", "text": text.strip() or "…",
                "buttons": [{"type": "web_url", "url": b["url"], "title": qr_title(b["text"]),
                             "webview_height_ratio": "full"} for b in url_buttons[:3]]}}}
            try:
                await self.channel.send(chat, message, tag)
                return {"message_id": self.next_id(), "chat": {"id": chat}}
            except MetaError as e:
                log.info("[%s] Шаблон із кнопками не прийнято (%s), надсилаю посиланням", self.tenant.name, e.message)
        # Довгі підписи кнопок (послуги з ціною тощо) — нумерованим списком у тексті, а кнопки — номери.
        numbered = any(utf16_len(t) > TITLE_MAX for t, p in options if p.startswith("cb:"))
        if numbered:
            text += "\n\n" + "\n".join(f"{i}. {t}" for i, (t, p) in enumerate(options, 1) if p != "phone")
        if links:
            text += "\n\n" + "\n".join(links)
        if options:
            self.pages[chat] = {"options": options, "numbered": numbered}
        chunks = split_text(text.strip() or "…", TEXT_LIMIT[platform])
        for i, chunk in enumerate(chunks):
            message: dict = {"text": chunk}
            if options and i == len(chunks) - 1:
                message["quick_replies"] = self._quick_replies(options, numbered, 0)
            await self.channel.send(chat, message, tag)
        return {"message_id": self.next_id(), "chat": {"id": chat}}

    async def send_page(self, chat: int, page: int) -> None:
        """Наступна/попередня сторінка кнопок («▶️»), коли їх більше, ніж вміщує Meta."""
        state = self.pages.get(chat)
        if not state:
            return
        options, numbered = state["options"], state["numbered"]
        pages = (len(options) - 1) // QR_PAGE + 1
        page = max(0, min(page, pages - 1))
        if numbered:
            lines = [f"{i}. {t}" for i, (t, _) in enumerate(options, 1)][page * QR_PAGE:(page + 1) * QR_PAGE]
            text = "\n".join(lines)
        else:
            text = "⬇️"
        await self._guard(self.channel.send(chat, {"text": text,
                                                   "quick_replies": self._quick_replies(options, numbered, page)}))

    async def _copy_from_meta(self, params: dict) -> dict:
        """Фото/файл клієнта з Meta → адміністратору в Telegram (за посиланням із вебхука)."""
        attachment = self.media.get((params["from_chat_id"], params.get("message_id")))
        if not attachment or not attachment.get("url"):
            raise TelegramError(400, "Bad Request: attachment is not available")
        url = attachment["url"]
        method, field = ("sendPhoto", "photo") if attachment.get("type") == "image" else ("sendDocument", "document")
        try:
            result = await self.tg.call(method, chat_id=params["chat_id"], **{field: url})
        except TelegramError:
            result = await self.tg.call("sendMessage", chat_id=params["chat_id"], text=f"📎 {url}")
        return result if isinstance(result, dict) else {"message_id": self.next_id()}


# ================================================================ вхідні події

class MetaGateway:
    """Події вебхука Meta → оновлення у форматі Telegram для BotApp."""

    def __init__(self, app, routers: dict[str, MetaRouter]):
        self.app = app
        self.routers = routers  # slug → MetaRouter
        self.by_page: dict[str, str] = {}
        self.by_ig: dict[str, str] = {}
        for slug, router in routers.items():
            self.by_page[router.channel.page_id] = slug
            if router.channel.ig_id:
                self.by_ig[router.channel.ig_id] = slug

    async def handle(self, payload: dict) -> None:
        kind = payload.get("object")
        platform = {"page": "messenger", "instagram": "instagram"}.get(kind)
        if platform is None:
            return
        for entry in payload.get("entry") or []:
            entry_id = str(entry.get("id") or "")
            slug = (self.by_ig if platform == "instagram" else self.by_page).get(entry_id)
            if slug is None and platform == "instagram":
                slug = self.by_page.get(entry_id)
            if slug is None:
                log.info("Meta: подія для невідомої сторінки %s", entry_id)
                continue
            for event in entry.get("messaging") or []:
                try:
                    await self.on_event(slug, platform, entry_id, event)
                except Exception:
                    log.exception("[%s] Помилка обробки події Meta", self.app.tenants[slug].name)

    async def on_event(self, slug: str, platform: str, entry_id: str, event: dict) -> None:
        router = self.routers[slug]
        channel = router.channel
        tenant = self.app.tenants[slug]
        sender = str((event.get("sender") or {}).get("id") or "")
        msg = event.get("message") or {}
        if not sender or sender in (entry_id, channel.page_id, channel.ig_id) or msg.get("is_echo"):
            return
        payload = (msg.get("quick_reply") or {}).get("payload") or (event.get("postback") or {}).get("payload")
        # Перехід за посиланням m.me/<сторінка>?ref=m<код> — запрошення майстра (як /start m<код> у Telegram).
        referral = event.get("referral") or (event.get("postback") or {}).get("referral") or {}
        ref = str(referral.get("ref") or "")
        if ref.startswith("m") and len(ref) > 1:
            msg, payload = {"text": f"/start {ref}"}, None
        if not msg and not payload:
            return  # прочитання, реакції тощо
        chat = channel.chat_id(platform, sender)
        user = channel.user(chat)
        if not user.get("first_name") and not user.get("profile_checked"):
            user.update({k: v for k, v in (await channel.fetch_profile(platform, sender)).items() if v})
            user["profile_checked"] = True
            channel.save_user(chat, user)

        if payload and payload.startswith("pg:"):
            await router.send_page(chat, int(payload[3:]) if payload[3:].isdigit() else 0)
            return
        if payload and payload.startswith("lang:"):
            code = payload[5:]
            if code not in tenant.languages:
                await self.ask_language(router, chat)
                return
            user["lang"] = code
            pending = user.pop("pending", None)
            channel.save_user(chat, user)
            await self.dispatch(slug, chat, user, pending or {"text": "/start"})
            return

        item = self.to_item(router, chat, msg, payload)
        if item is None:
            return
        if not user.get("lang"):
            if len(tenant.languages) == 1:
                user["lang"] = tenant.languages[0]
                channel.save_user(chat, user)
            else:
                user["pending"] = item
                channel.save_user(chat, user)
                await self.ask_language(router, chat)
                return
        await self.dispatch(slug, chat, user, item)

    @staticmethod
    def to_item(router: MetaRouter, chat: int, msg: dict, payload: str | None) -> dict | None:
        """Що зробив клієнт: {"data": кнопка} або {"text": …} / {"media": …}."""
        if payload and payload.startswith("cb:"):
            return {"data": payload[3:]}
        if payload and payload.startswith("txt:"):
            return {"text": payload[4:]}
        text = (msg.get("text") or "").strip()
        if text:
            return {"text": text}
        for att in msg.get("attachments") or []:
            kind = att.get("type") or "file"
            url = (att.get("payload") or {}).get("url")
            return {"media": kind, "url": url}
        return None

    async def ask_language(self, router: MetaRouter, chat: int) -> None:
        tenant = router.tenant
        text = "\n".join(TEXTS[lang]["meta_choose_lang"] for lang in tenant.languages)
        replies = [{"content_type": "text", "title": LANG_TITLES.get(lang, lang), "payload": f"lang:{lang}"}
                   for lang in tenant.languages]
        await router._guard(router.channel.send(chat, {"text": text, "quick_replies": replies}))

    async def dispatch(self, slug: str, chat: int, user: dict, item: dict) -> None:
        router = self.routers[slug]
        sender = {"id": chat, "first_name": user.get("first_name"), "last_name": user.get("last_name"),
                  "username": user.get("username"), "language_code": user.get("lang")}
        message_id = router.next_id()
        if "data" in item:
            cq_id = f"meta:{message_id}"
            router.remember_callback(cq_id, chat)
            update = {"callback_query": {"id": cq_id, "from": sender, "data": item["data"],
                                         "message": {"chat": {"id": chat, "type": "private"}}}}
        else:
            message = {"message_id": message_id, "from": sender, "chat": {"id": chat, "type": "private"}}
            if "text" in item:
                message["text"] = item["text"]
            else:
                kind = item.get("media")
                router.remember_media(chat, message_id, {"type": kind, "url": item.get("url")})
                key = {"image": "photo", "audio": "voice", "video": "video"}.get(kind, "document")
                message[key] = [{}] if key == "photo" else {}
            update = {"message": message}
        await self.app.handle_update(slug, update)


# ================================================================ вебхук

class MetaWebhook:
    """Обробник вебхука Meta (/meta/webhook) для HTTP-сервера бота (barberbot/web.py)."""

    PATH = "/meta/webhook"

    def __init__(self, app, gateway: MetaGateway, settings):
        self.app = app
        self.gateway = gateway
        self.secret = settings.meta_app_secret.encode("utf-8")
        self.verify_token = settings.meta_verify_token

    def signature_ok(self, body: bytes, header: str) -> bool:
        expected = "sha256=" + hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, header or "")

    async def respond(self, method: str, target: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        parts = urllib.parse.urlsplit(target)
        if parts.path == "/health":
            return 200, "ok"
        if parts.path != self.PATH:
            return 404, "not found"
        if method == "GET":
            q = dict(urllib.parse.parse_qsl(parts.query))
            if q.get("hub.mode") == "subscribe" and self.verify_token \
                    and hmac.compare_digest(q.get("hub.verify_token", ""), self.verify_token):
                return 200, q.get("hub.challenge", "")
            return 403, "forbidden"
        if method != "POST":
            return 405, "method not allowed"
        if not self.signature_ok(body, headers.get("x-hub-signature-256", "")):
            log.warning("Meta: вебхук із неправильним підписом відхилено")
            return 403, "bad signature"
        try:
            payload = json.loads(body.decode("utf-8"))
        except ValueError:
            return 400, "bad json"
        self.app.spawn(self.gateway.handle(payload))
        return 200, "EVENT_RECEIVED"
