"""Instagram Direct і Messenger: вебхук Meta → бот → Send API Meta."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import unittest
import urllib.parse

from barberbot import clock
from barberbot.app import BotApp
from barberbot.db import DB
from barberbot.meta import FB_BASE, IG_BASE, MetaWebhook, html_to_text, platform_of, split_text
from barberbot.web import WebServer

from .helpers import ADMIN_ID, FakeLLM, FakeTelegram, make_settings, make_tenant, set_time, text_reply

PAGE, IG = "1001", "1789"
META_TOML = f'\n[meta]\npage_id = "{PAGE}"\ninstagram_id = "{IG}"\npage_access_token = "EAAtest"\n'


class FakeGraph:
    """Підробка Graph API: записує запити, відповідає успіхом (або заданими помилками)."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.errors: list[dict] = []

    def __call__(self, method: str, url: str, body: bytes | None) -> tuple[int, bytes]:
        data = json.loads(body) if body else None
        self.calls.append((method, url, data))
        if method == "POST" and self.errors:
            return 400, json.dumps({"error": self.errors.pop(0)}).encode()
        if method == "GET":
            return 200, json.dumps({"name": "Anna Kovács", "username": "anna.k"}).encode()
        return 200, b'{"recipient_id": "x", "message_id": "m"}'

    def sent(self) -> list[dict]:
        return [b for m, _, b in self.calls if m == "POST" and b and "message" in b]

    def last(self) -> dict:
        return self.sent()[-1]["message"]

    def texts(self) -> list[str]:
        return [b["message"]["text"] for b in self.sent()]


def ig_event(sender: str, text: str | None = None, payload: str | None = None, attachment: dict | None = None):
    message: dict = {"mid": "m1"}
    if text is not None:
        message["text"] = text
    if payload is not None:
        message["quick_reply"] = {"payload": payload}
        message.setdefault("text", payload)
    if attachment is not None:
        message["attachments"] = [attachment]
    return {"object": "instagram", "entry": [{"id": IG, "time": 1, "messaging": [
        {"sender": {"id": sender}, "recipient": {"id": IG}, "timestamp": 1, "message": message}]}]}


def fb_event(sender: str, text: str):
    return {"object": "page", "entry": [{"id": PAGE, "time": 1, "messaging": [
        {"sender": {"id": sender}, "recipient": {"id": PAGE}, "timestamp": 1, "message": {"mid": "m", "text": text}}]}]}


class MetaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        set_time(2026, 10, 26, 9, 0)
        self.tenant = make_tenant(extra=META_TOML)
        self.db = DB(":memory:")
        self.tg = FakeTelegram()
        self.graph = FakeGraph()
        self.llm = FakeLLM()
        self.settings = make_settings(meta_app_secret="appsecret", meta_verify_token="verify-me", meta_webhook_port=0)
        self.app = BotApp(self.settings, [self.tenant], self.db, self.llm, api_factory=lambda t: self.tg,
                          meta_transport=self.graph)

    async def asyncTearDown(self):
        clock.set_fixed(None)
        self.db.close()

    async def event(self, payload: dict) -> None:
        await self.app.meta.handle(payload)

    def qr(self) -> list[tuple[str, str]]:
        return [(q.get("title", ""), q.get("payload", q["content_type"])) for q in self.graph.last().get("quick_replies", [])]

    async def test_instagram_client_books_with_quick_replies(self):
        await self.event(ig_event("igs-1", "Hi"))
        picker = self.graph.last()
        self.assertIn("🌐 Choose your language:", picker["text"])
        self.assertIn(("🇭🇺 Magyar", "lang:hu"), self.qr())
        # Профіль з Instagram підтягнуто.
        self.assertTrue(any(m == "GET" and "fields=name%2Cusername" in u for m, u, _ in self.graph.calls))

        self.llm.add(text_reply("Hello! How can I help?"))
        await self.event(ig_event("igs-1", payload="lang:en"))  # після вибору мови — відповідь на «Hi»
        self.assertEqual(self.graph.last()["text"], "Hello! How can I help?")
        self.assertIn(("📅 Book", "txt:📅 Book"), self.qr())
        self.assertIn(("🌐 Language", "lang:?"), self.qr())

        await self.event(ig_event("igs-1", payload="txt:📅 Book"))
        services = self.graph.last()
        self.assertIn("1. Чоловіча стрижка · 500 грн", services["text"])  # довгі підписи — нумерованим списком
        self.assertEqual(self.qr()[0], ("1", "cb:bs:haircut"))
        self.assertNotIn("<b>", " ".join(self.graph.texts()))

        await self.event(ig_event("igs-1", payload="cb:bs:haircut"))
        self.assertIn(("Андрій", "cb:bm:haircut:andriy"), self.qr())
        await self.event(ig_event("igs-1", payload="cb:bm:haircut:andriy"))
        days = self.qr()
        self.assertEqual(len(days), 13)  # 12 робочих днів + «Назад» — рівно максимум Meta
        self.assertIn(("Tomorrow", "cb:bd:haircut:andriy:20261027"), days)

        await self.event(ig_event("igs-1", payload="cb:bd:haircut:andriy:20261027"))
        times = self.qr()
        self.assertEqual(len(times), 12)  # 17 варіантів часу + «Назад» не вміщаються: 11 + «▶️»
        self.assertEqual(times[-1], ("▶️", "pg:1"))
        await self.event(ig_event("igs-1", payload="pg:1"))
        self.assertEqual(self.qr()[0], ("◀️", "pg:0"))
        self.assertIn(("⬅️ Back", "cb:bm:haircut:andriy"), self.qr())
        await self.event(ig_event("igs-1", payload="cb:bt:haircut:andriy:20261027:1200"))
        self.assertIn("Please check", self.graph.last()["text"])
        await self.event(ig_event("igs-1", payload="cb:bc:haircut:andriy:20261027:1200"))
        self.assertIn("phone number", self.graph.last()["text"])
        self.assertEqual(self.qr(), [("Cancel", "txt:Cancel")])  # в Instagram немає кнопки «поділитися номером»

        await self.event(ig_event("igs-1", "+380501234567"))
        booked = self.graph.texts()[-1]
        self.assertIn("Done, you're booked!", booked)
        b = self.db.get_booking(1)
        self.assertEqual((b["service_id"], b["master_id"], b["start_at"]), ("haircut", "andriy", "2026-10-27 12:00"))
        client = self.db.get_client(b["client_id"])
        self.assertEqual(platform_of(client["tg_id"]), "instagram")
        self.assertEqual(client["username"], "anna.k")
        admin_note = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Anna Kovács · 📷 Instagram · @anna.k", admin_note)
        # Жодного виклику Telegram для клієнта з Instagram.
        self.assertFalse([p for _, p in self.tg.calls if platform_of(p.get("chat_id"))])

    async def test_messenger_reminder_outside_window_uses_tag(self):
        await self.event(fb_event("psid-9", "/start"))  # вибір мови
        chat = self.app.meta_routers[self.tenant.slug].channel.chat_id("messenger", "psid-9")
        self.assertGreaterEqual(chat, FB_BASE)
        self.graph.errors.append({"code": 10, "error_subcode": 2018278, "message": "outside of allowed window"})
        sent = await self.app.send(self.tenant, chat, "<b>Reminder</b>", tag="event")
        self.assertIsNotNone(sent)
        retry = self.graph.sent()[-1]
        self.assertEqual((retry["messaging_type"], retry["tag"]), ("MESSAGE_TAG", "CONFIRMED_EVENT_UPDATE"))
        self.assertEqual(retry["message"]["text"], "Reminder")

    async def test_photo_from_instagram_goes_to_admin(self):
        await self.event(ig_event("igs-2", payload="lang:uk"))  # мова → /start
        self.graph.calls.clear()
        await self.event(ig_event("igs-2", attachment={"type": "image", "payload": {"url": "https://cdn.example/p.jpg"}}))
        self.assertEqual(self.tg.of("sendPhoto", ADMIN_ID)[-1]["photo"], "https://cdn.example/p.jpg")
        self.assertIn("адміністратору", self.graph.last()["text"])

    async def test_webhook_verification_and_signature(self):
        hook = MetaWebhook(self.app, self.app.meta, self.settings)
        ok = await hook.respond("GET", "/meta/webhook?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=42",
                                {}, b"")
        self.assertEqual(ok, (200, "42"))
        bad = await hook.respond("GET", "/meta/webhook?hub.mode=subscribe&hub.verify_token=nope&hub.challenge=42",
                                 {}, b"")
        self.assertEqual(bad[0], 403)
        body = json.dumps(ig_event("igs-3", "Hi")).encode()
        self.assertEqual((await hook.respond("POST", "/meta/webhook", {"x-hub-signature-256": "sha256=00"}, body))[0],
                         403)
        self.assertEqual(self.graph.calls, [])

    async def test_webhook_http_server(self):
        hook = WebServer(self.settings, MetaWebhook(self.app, self.app.meta, self.settings))
        await hook.start()
        port = hook.server.sockets[0].getsockname()[1]
        body = json.dumps(ig_event("igs-4", "Hi")).encode()
        sig = "sha256=" + hmac.new(b"appsecret", body, hashlib.sha256).hexdigest()
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(f"POST /meta/webhook HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
                     f"X-Hub-Signature-256: {sig}\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body)
        await writer.drain()
        response = await reader.read()
        writer.close()
        await hook.stop()
        self.assertTrue(response.startswith(b"HTTP/1.1 200"))
        self.assertIn(b"EVENT_RECEIVED", response)
        for _ in range(50):
            if self.graph.sent():
                break
            await asyncio.sleep(0.02)
        self.assertIn("🌐", self.graph.last()["text"])

    async def test_book_opens_webapp_button_in_messenger(self):
        self.app.settings.web_base_url = "https://bot.example.com"
        from barberbot.webapp import WebApp
        self.app.webapp = WebApp(self.app)
        await self.event(fb_event("psid-7", "Hi"))  # вибір мови
        self.llm.add(text_reply("Szia!"))  # після вибору мови бот відповідає на «Hi»
        await self.event({"object": "page", "entry": [{"id": PAGE, "messaging": [{"sender": {"id": "psid-7"},
            "message": {"mid": "m", "text": "lang:hu", "quick_reply": {"payload": "lang:hu"}}}]}]})
        await self.event({"object": "page", "entry": [{"id": PAGE, "messaging": [{"sender": {"id": "psid-7"},
            "message": {"mid": "m", "text": "x", "quick_reply": {"payload": "txt:📅 Időpontfoglalás"}}}]}]})
        tpl = self.graph.last()["attachment"]["payload"]
        self.assertEqual(tpl["template_type"], "button")
        button = tpl["buttons"][0]
        self.assertEqual((button["type"], button["title"]), ("web_url", "📅 Online foglalás"))
        chat = self.app.meta_routers[self.tenant.slug].channel.chat_id("messenger", "psid-7")
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(button["url"]).query)["u"][0]
        self.assertEqual(self.app.webapp.verify(self.tenant.slug, token), chat)

    def test_helpers(self):
        self.assertEqual(html_to_text("<b>Ціна</b> &amp; час"), "Ціна & час")
        self.assertEqual(platform_of(IG_BASE + 5), "instagram")
        self.assertEqual(platform_of(FB_BASE + 5), "messenger")
        self.assertIsNone(platform_of(123456789))
        parts = split_text("рядок\n" * 300, 1000)
        self.assertTrue(all(len(p) <= 1000 for p in parts))
        self.assertEqual("".join(parts).count("рядок"), 300)


if __name__ == "__main__":
    unittest.main()
