"""Міні-застосунок онлайн-запису: сторінка, API, вхід через Telegram і підписане посилання."""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest
import urllib.parse
from datetime import datetime

from barberbot import clock
from barberbot.app import BotApp
from barberbot.db import DB
from barberbot.webapp import telegram_user

from .helpers import ADMIN_ID, CLIENT_ID, FakeLLM, FakeTelegram, TOKEN, make_settings, make_tenant, msg, set_time


def init_data(user: dict, token: str = TOKEN, auth_date: int | None = None) -> str:
    """initData так, як його підписує Telegram."""
    fields = {"auth_date": str(auth_date or int(clock.utcnow().timestamp())), "query_id": "AAE1",
              "user": json.dumps(user, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(fields)


class WebAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        set_time(2026, 10, 26, 9, 0)  # понеділок
        self.tenant = make_tenant()
        self.db = DB(":memory:")
        self.tg = FakeTelegram()
        self.app = BotApp(make_settings(web_base_url="https://bot.example.com"), [self.tenant], self.db, FakeLLM(),
                          api_factory=lambda t: self.tg)
        self.web = self.app.webapp
        self.base = f"/app/{self.tenant.slug}/"

    async def asyncTearDown(self):
        clock.set_fixed(None)
        self.db.close()

    async def get(self, path: str, headers: dict | None = None):
        r = await self.web.handle("GET", self.base + path, headers or {}, b"")
        return r.status, (json.loads(r.body) if r.content_type.startswith("application/json") else r.body)

    async def book(self, data: dict, headers: dict | None = None):
        body = {"service": "haircut", "master": "andriy", "date": "2026-10-27", "time": "12:00", "lang": "uk", **data}
        r = await self.web.handle("POST", self.base + "api/book", {"x-forwarded-for": "1.2.3.4", **(headers or {})},
                                  json.dumps(body).encode())
        return r.status, json.loads(r.body)

    async def test_page_and_unknown_tenant(self):
        status, body = await self.get("")
        self.assertEqual(status, 200)
        self.assertIn(b"telegram-web-app.js", body)
        r = await self.web.handle("GET", "/app/nope/", {}, b"")
        self.assertEqual(r.status, 404)
        r = await self.web.handle("GET", f"/app/{self.tenant.slug}?lang=en", {}, b"")
        self.assertEqual((r.status, r.headers["Location"]), (301, f"/app/{self.tenant.slug}/?lang=en"))

    async def test_config_days_and_slots(self):
        status, cfg = await self.get("api/config?lang=en")
        self.assertEqual((status, cfg["lang"], cfg["name"]), (200, "en", "Тест Барбер"))
        haircut = cfg["groups"][0]["services"][0]
        self.assertEqual((haircut["id"], haircut["price_text"], haircut["duration"]), ("haircut", "500 грн", 60))
        self.assertEqual({m["id"] for m in cfg["masters"]}, {"andriy", "oleg"})
        self.assertFalse(cfg["client"]["known"])

        _, days = await self.get("api/days?service=haircut&master=oleg")
        self.assertEqual(days["days"][0], {"date": "2026-10-26", "open": False})  # понеділок у Олега вихідний
        self.assertTrue(days["days"][1]["open"])
        _, slots = await self.get("api/slots?service=haircut&master=any&date=2026-10-27")
        self.assertEqual(slots["times"][0], "10:00")
        status, _ = await self.get("api/slots?service=nope&master=any&date=2026-10-27")
        self.assertEqual(status, 400)

    async def test_anonymous_booking(self):
        status, r = await self.book({"name": "Анна", "phone": ""})
        self.assertEqual(status, 400)  # без телефону не записуємо
        status, r = await self.book({"name": "Анна", "phone": "+380 67 111 22 33"})
        self.assertEqual(status, 200, r)
        self.assertEqual((r["booking"]["service"], r["booking"]["time"], r["booking"]["in_chat"]), ("Чоловіча стрижка", "12:00", False))
        b = self.db.get_booking(r["booking"]["id"])
        client = self.db.get_client(b["client_id"])
        self.assertLess(client["tg_id"], 0)
        self.assertEqual((client["name"], client["phone"]), ("Анна", "+380671112233"))
        self.assertIn("через онлайн-запис", self.tg.last(ADMIN_ID)["text"])
        # Той самий час уже зайнятий — зрозуміла помилка.
        status, r = await self.book({"name": "Іра", "phone": "+380 67 999 88 77"})
        self.assertEqual(status, 409)
        self.assertIn("зайняли", r["message"])

    async def test_telegram_user_books_and_gets_chat_confirmation(self):
        await self.app.handle_update(self.tenant.slug, msg(text="/start"))
        self.db.set_client_field(self.db.get_client_by_tg(self.tenant.slug, CLIENT_ID)["id"], "phone", "+380501234567")
        user = {"id": CLIENT_ID, "first_name": "Іван", "language_code": "uk"}
        headers = {"x-telegram-init-data": init_data(user)}
        _, cfg = await self.get("api/config", headers)
        self.assertEqual(cfg["client"], {"known": True, "name": "Іван", "phone": "+380501234567"})
        status, r = await self.book({}, headers)
        self.assertEqual(status, 200, r)
        self.assertTrue(r["booking"]["in_chat"])
        self.assertIn("Готово, ви записані", self.tg.last(CLIENT_ID)["text"])

        # Підроблений підпис — це вже не Іван, а анонім без контактів.
        forged = init_data(user).replace("hash=", "hash=0")
        status, _ = await self.book({"time": "15:00"}, {"x-telegram-init-data": forged})
        self.assertEqual(status, 400)
        self.assertIsNone(telegram_user(TOKEN, init_data(user, auth_date=1)))  # прострочений

    async def test_signed_link_identifies_chat(self):
        await self.app.handle_update(self.tenant.slug, msg(text="/start"))
        url = self.web.url(self.tenant, CLIENT_ID, "uk")
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["u"][0]
        self.assertEqual(self.web.verify(self.tenant.slug, token), CLIENT_ID)
        self.assertIsNone(self.web.verify(self.tenant.slug, f"{CLIENT_ID}.deadbeef"))
        status, r = await self.book({"phone": "+380501234567", "token": token})
        self.assertEqual(status, 200, r)
        self.assertEqual(self.db.get_booking(r["booking"]["id"])["client_id"],
                         self.db.get_client_by_tg(self.tenant.slug, CLIENT_ID)["id"])

    async def test_rate_limit(self):
        for i in range(10):
            self.web._rate_ok("1.2.3.4")
        status, r = await self.book({"name": "Анна", "phone": "+380 67 111 22 33"})
        self.assertEqual(status, 429)

    async def test_bot_buttons(self):
        await self.app.setup_commands(self.tenant.slug)
        button = self.tg.of("setChatMenuButton")[-1]["menu_button"]
        self.assertEqual(button["type"], "web_app")
        self.assertEqual(button["web_app"]["url"], f"https://bot.example.com/app/{self.tenant.slug}/")
        await self.app.handle_update(self.tenant.slug, msg(text="📅 Записатися"))
        first = self.tg.last(CLIENT_ID)["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(first["web_app"]["url"], f"https://bot.example.com/app/{self.tenant.slug}/")


if __name__ == "__main__":
    unittest.main()
