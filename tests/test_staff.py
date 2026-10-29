"""Помічник персоналу: текст і голос у боті, адмінка на телефоні (API), Siri, MCP, Web Push."""

from __future__ import annotations

import json
import unittest
from datetime import datetime

from barberbot import webpush
from barberbot.app import BotApp
from barberbot.staff import staff_user

from .helpers import ADMIN_ID, CLIENT_ID, last_tool_result, make_settings, msg, text_reply, tool_call
from .test_masters import MASTER_ID, MasterTestCase


class StaffChatTests(MasterTestCase):
    async def test_master_schedule_is_only_his_own(self):
        await self.link()
        self.llm.add(tool_call(("get_schedule", {"date": "2026-10-27"})),
                     text_reply("Завтра о 14:00 — Олена, борода."))
        await self.master("Хто в мене завтра?")
        payload = self.llm.payloads[0]
        self.assertIn("помічник персоналу", payload["system"][0]["text"])
        self.assertIn("майстер Олег", payload["system"][0]["text"])
        self.assertIn("block_time", [t["name"] for t in payload["tools"]])
        day = last_tool_result(self.llm.payloads[1])["days"][0]
        self.assertEqual([b["client"] for b in day["bookings"]], ["Олена"])  # запису Івана до Андрія не видно
        self.assertEqual(list(day["hours"]), ["Олег"])
        self.assertEqual(self.last()["text"], "Завтра о 14:00 — Олена, борода.")

    async def test_schedule_shows_blocks_of_masters(self):
        await self.link()
        self.booking.add_block("oleg", datetime(2026, 10, 27, 16, 0), datetime(2026, 10, 27, 17, 0), "обід")
        self.booking.add_block("andriy", datetime(2026, 10, 27, 9, 0), datetime(2026, 10, 27, 10, 0), "")
        u = staff_user(self.app, self.tenant, MASTER_ID)
        blocks = self.app.staff.ops.schedule(u, "2026-10-27")["days"][0]["blocks"]
        self.assertEqual([(b["master"], b["range"], b["can_open"]) for b in blocks], [("Олег", "16:00–17:00", False)])

    async def test_master_blocks_time_with_confirmation_button(self):
        await self.link()
        self.llm.add(tool_call(("block_time", {"date": "2026-10-27", "time_from": "13:00", "time_to": "15:00"})),
                     text_reply("Закрити завтра з 13:00 до 15:00? Підтверджуєте?"))
        await self.master("Закрий мені завтра з першої до третьої")
        card = self.last()
        self.assertIn("Закрити час: <b>Олег</b>", card["text"])
        self.assertIn("На цей час уже є записи", card["text"])  # о 14:00 — Олена
        self.assertFalse(self.db.future_blocks(self.slug, self.tenant.now()))
        await self.press(self.tg.button(card, "sY:")["callback_data"])
        blocks = self.db.future_blocks(self.slug, self.tenant.now())
        self.assertEqual([(b["master_id"], b["start_at"], b["end_at"], b["created_by"]) for b in blocks],
                         [("oleg", "2026-10-27 13:00", "2026-10-27 15:00", "master")])
        self.assertIn("Готово", self.last()["text"])
        self.assertIn("Майстер <b>Олег</b> закрив час", self.tg.last(ADMIN_ID)["text"])
        await self.press(self.tg.button(card, "sY:")["callback_data"])  # повторне натискання — дія вже виконана
        self.assertIn("неактуальна", self.last()["text"])
        self.assertEqual(len(self.db.future_blocks(self.slug, self.tenant.now())), 1)

    async def test_yes_and_no_by_text(self):
        await self.link()
        self.llm.add(tool_call(("block_time", {"date": "2026-10-28"})), text_reply("Закрити середу? Підтверджуєте?"),
                     tool_call(("block_time", {"date": "2026-10-29"})), text_reply("Закрити четвер?"))
        await self.master("закрий середу")
        await self.master("ні")
        self.assertIn("нічого не змінюю", self.last()["text"])
        await self.master("а четвер закрий")
        await self.master("Так")
        self.assertEqual([b["start_at"] for b in self.db.future_blocks(self.slug, self.tenant.now())],
                         ["2026-10-29 00:00"])
        self.assertEqual(len(self.llm.payloads), 4)  # «так» і «ні» — без звернення до AI

    async def test_master_cannot_cancel_clients(self):
        await self.link()
        self.llm.add(tool_call(("cancel_booking", {"booking_id": self.b_oleg["id"]})),
                     text_reply("Скасувати може лише власник."))
        await self.master("скасуй Олену")
        self.assertEqual(last_tool_result(self.llm.payloads[1])["error"], "owner_only")
        self.assertEqual(self.db.get_booking(self.b_oleg["id"])["status"], "active")
        self.llm.add(tool_call(("mark_no_show", {"booking_id": self.b_andriy["id"]})), text_reply("Це не ваш запис."))
        await self.master("Іван не прийшов")
        self.assertEqual(last_tool_result(self.llm.payloads[3])["error"], "not_yours")

    async def test_owner_cancels_and_client_is_notified(self):
        await self.link()
        self.llm.add(tool_call(("cancel_booking", {"booking_id": self.b_andriy["id"]})),
                     text_reply("Скасувати запис Івана завтра о 12:00? Підтверджуєте?"))
        await self.admin("скасуй Івана на завтра")
        await self.admin("так")
        self.assertEqual(self.db.get_booking(self.b_andriy["id"])["status"], "cancelled")
        self.assertIn("клієнт отримав повідомлення", self.tg.last(ADMIN_ID)["text"].lower())
        self.assertIn("скасовано адміністратором", self.tg.last(CLIENT_ID)["text"])

    async def test_owner_books_new_client_for_master(self):
        await self.link()
        self.llm.add(tool_call(("create_booking", {"service_id": "beard", "date": "2026-10-27", "time": "16:00",
                                                   "master_id": "oleg", "client_name": "Андраш",
                                                   "client_phone": "+36 30 123 4567"})),
                     text_reply("Записати Андраша завтра о 16:00 до Олега? Підтверджуєте?"))
        await self.admin("запиши Андраша на бороду завтра о 4 до Олега, телефон +36 30 123 4567")
        self.assertIn("Записати <b>Андраш · +36301234567</b>", self.tg.last(ADMIN_ID)["text"])
        await self.admin("так")
        b = self.db.q("SELECT * FROM bookings WHERE start_at = '2026-10-27 16:00'")[0]
        self.assertEqual((b["master_id"], b["service_id"], b["source"]), ("oleg", "beard", "admin"))
        self.assertIn("Бот не може повідомити клієнта", self.tg.last(ADMIN_ID)["text"])
        self.assertIn("Новий запис до вас", self.last()["text"])  # майстер отримав сповіщення

    async def test_no_ai_key(self):
        app = BotApp(make_settings(), [self.tenant], self.db, None, api_factory=lambda t: self.tg)
        await app.handle_update(self.slug, msg(uid=ADMIN_ID, text="хто завтра?"))
        self.assertIn("Помічник зараз недоступний", self.tg.last(ADMIN_ID)["text"])


class VoiceTests(MasterTestCase):
    async def test_voice_message_points_to_phone_dictation(self):
        await self.link()
        await self.send(msg(uid=MASTER_ID, voice={"file_id": "v1"}))
        self.assertIn("натисніть 🎤 на клавіатурі", self.last()["text"])
        await self.send(msg(voice={"file_id": "v2"}))
        self.assertIn("Голосові я поки не слухаю", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(self.llm.payloads, [])


class StaffWebTests(MasterTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.settings.web_base_url = "https://bot.example.com"
        self.app = BotApp(self.settings, [self.tenant], self.db, self.llm, api_factory=lambda t: self.tg)
        self.booking = self.app.bookings[self.slug]
        self.web = self.app.staff_web
        self.base = f"/staff/{self.slug}/"

    async def login(self, uid: int = ADMIN_ID) -> dict:
        await self.send(msg(uid=uid, text="/app"))
        url = self.tg.buttons(self.tg.last(uid))[0]["url"]
        self.assertTrue(url.startswith(f"https://bot.example.com{self.base}login?t="))
        r = await self.web.handle("GET", url.removeprefix("https://bot.example.com"), {}, b"")
        self.assertEqual(r.status, 303)
        cookie = r.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        r2 = await self.web.handle("GET", url.removeprefix("https://bot.example.com"), {}, b"")
        self.assertEqual(r2.status, 403)  # посилання одноразове
        return {"cookie": cookie.split(";")[0], "x-requested-with": "staff"}

    async def call(self, method: str, path: str, headers: dict, data: dict | None = None):
        r = await self.web.handle(method, self.base + path, headers, json.dumps(data or {}).encode())
        return r.status, (json.loads(r.body) if r.content_type.startswith("application/json") else r.body)

    async def test_pages_and_auth(self):
        for path in ("", "sw.js", "manifest.webmanifest"):
            r = await self.web.handle("GET", self.base + path, {}, b"")
            self.assertEqual(r.status, 200, path)
        manifest = json.loads((await self.web.handle("GET", self.base + "manifest.webmanifest", {}, b"")).body)
        self.assertEqual(manifest["start_url"], self.base)
        icon = await self.web.handle("GET", self.base + "icon-192.png", {}, b"")
        self.assertTrue(icon.body.startswith(b"\x89PNG"))
        status, _ = await self.call("GET", "api/me", {})
        self.assertEqual(status, 401)
        await self.send(msg(text="/app"))  # клієнт — не персонал
        self.assertIn("Не знаю такої команди", self.tg.last(CLIENT_ID)["text"])

    async def test_owner_day_and_block_via_api(self):
        h = await self.login()
        status, me = await self.call("GET", "api/me", h)
        self.assertEqual((status, me["role"], me["shop"]), (200, "owner", "Тест Барбер"))
        _, day = await self.call("GET", "api/day?date=2026-10-27", h)
        self.assertEqual(sorted(b["client"] for b in day["days"][0]["bookings"]), ["Іван", "Олена"])
        status, _ = await self.call("POST", "api/propose", {"cookie": h["cookie"]}, {"kind": "block"})
        self.assertEqual(status, 403)  # без заголовка X-Requested-With
        status, plan = await self.call("POST", "api/propose", h, {"kind": "block", "date": "2026-10-28",
                                                                    "master_id": "andriy"})
        self.assertEqual(status, 200)
        self.assertIn("Закрити час: Андрій", plan["summary"])
        status, done = await self.call("POST", "api/confirm", h, {"action_id": plan["action_id"]})
        self.assertTrue(done["done"])
        self.assertEqual(self.db.future_blocks(self.slug, self.tenant.now())[0]["master_id"], "andriy")
        status, err = await self.call("POST", "api/propose", h, {"kind": "cancel", "booking_id": 99999})
        self.assertEqual((status, err["error"]), (400, "not_found"))

    async def test_master_sees_only_own_and_chats_are_owner_only(self):
        await self.link()
        h = await self.login(MASTER_ID)
        _, day = await self.call("GET", "api/day?date=2026-10-27", h)
        self.assertEqual([b["client"] for b in day["days"][0]["bookings"]], ["Олена"])
        status, err = await self.call("GET", "api/chats", h)
        self.assertEqual((status, err["error"]), (400, "owner_only"))

    async def test_ask_and_siri_key(self):
        h = await self.login()
        self.llm.add(text_reply("Завтра два записи: о 12:00 Іван і о 14:00 Олена."))
        status, reply = await self.call("POST", "api/ask", h, {"text": "що завтра?"})
        self.assertEqual(reply["text"], "Завтра два записи: о 12:00 Іван і о 14:00 Олена.")
        _, key = await self.call("POST", "api/key", h)
        siri = {"authorization": f"Bearer {key['key']}"}
        self.llm.add(text_reply("Завтра два записи."))
        r = await self.web.handle("POST", self.base + "api/ask?format=text", siri,
                                  json.dumps({"text": "що завтра"}).encode())
        self.assertEqual((r.status, r.body.decode()), (200, "Завтра два записи."))
        status, _ = await self.call("GET", "api/day", siri)
        self.assertEqual(status, 403)  # ключ Siri — лише для запитань
        _, key2 = await self.call("POST", "api/key", h)  # новий ключ скасовує старий
        r = await self.web.handle("POST", self.base + "api/ask", siri, b'{"text": "x"}')
        self.assertEqual(r.status, 401)
        self.assertNotEqual(key["key"], key2["key"])

    async def test_mcp_connector(self):
        h = await self.login()
        _, key = await self.call("POST", "api/key", h)
        path = key["mcp_url"].removeprefix("https://bot.example.com")

        async def rpc(method: str, params: dict | None = None, req_id: int | None = 1):
            body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
            if req_id is not None:
                body["id"] = req_id
            r = await self.web.handle("POST", path, {}, json.dumps(body).encode())
            return r.status, (json.loads(r.body) if r.body else None)

        status, init = await rpc("initialize", {"protocolVersion": "2025-06-18"})
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual((await rpc("notifications/initialized", req_id=None))[0], 202)
        _, tools = await rpc("tools/list")
        names = [t["name"] for t in tools["result"]["tools"]]
        self.assertIn("get_schedule", names)
        self.assertIn("confirm_action", names)
        _, res = await rpc("tools/call", {"name": "cancel_booking", "arguments": {"booking_id": self.b_oleg["id"]}})
        prepared = res["result"]["structuredContent"]
        self.assertEqual(prepared["status"], "awaiting_confirmation")
        self.assertEqual(self.db.get_booking(self.b_oleg["id"])["status"], "active")
        _, res = await rpc("tools/call", {"name": "confirm_action", "arguments": {"action_id": prepared["action_id"]}})
        self.assertFalse(res["result"]["isError"])
        self.assertEqual(self.db.get_booking(self.b_oleg["id"])["status"], "cancelled")
        r = await self.web.handle("POST", f"/mcp/{self.slug}/{'x' * 40}", {}, b"{}")
        self.assertEqual(r.status, 404)  # не 401: інакше claude.ai вимагатиме вхід OAuth для всього сервера

    async def mcp_rpc(self, uid: int = ADMIN_ID):
        h = await self.login(uid)
        _, key = await self.call("POST", "api/key", h)
        path = key["mcp_url"].removeprefix("https://bot.example.com")

        async def tool(name: str, arguments: dict | None = None) -> dict:
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}}}
            r = await self.web.handle("POST", path, {}, json.dumps(body).encode())
            return json.loads(r.body)["result"]["structuredContent"]

        async def confirm(prepared: dict) -> dict:
            self.assertIn("action_id", prepared, prepared)
            return await tool("confirm_action", {"action_id": prepared["action_id"]})

        return tool, confirm

    async def test_mcp_owner_admin_tools(self):
        tool, confirm = await self.mcp_rpc()
        shop = await tool("get_shop")
        self.assertEqual(shop["client_ai"], "on")
        self.assertEqual({m["master_id"] for m in shop["masters"]}, {"andriy", "oleg"})
        # ціна: підготувати → ще стара → підтвердити → нова
        prepared = await tool("set_price", {"service_id": "beard", "price": 350})
        self.assertIn("Борода", prepared["summary"])
        self.assertEqual(self.tenant.services["beard"].price, 300)
        self.assertTrue((await confirm(prepared))["ok"])
        self.assertEqual(self.tenant.services["beard"].price, 350)
        self.assertEqual((await tool("set_price", {"service_id": "beard", "price": 350}))["error"], "same_price")
        await confirm(await tool("set_price", {"service_id": "beard"}))  # повернути ціну з файлу
        self.assertEqual(self.tenant.services["beard"].price, 300)
        # AI для клієнтів
        await confirm(await tool("set_client_ai", {"on": False}))
        self.assertEqual(self.app.ai_status(self.tenant), "paused")
        await confirm(await tool("set_client_ai", {"on": True}))
        self.assertEqual(self.app.ai_status(self.tenant), "on")
        # звіт за довільний період і Excel у Telegram
        report = await tool("get_report", {"days": 90})
        self.assertEqual((report["period"], "bot" in report), ("custom", True))
        await confirm(await tool("export_bookings", {"days": 7}))
        self.assertTrue(self.tg.of("sendDocument", ADMIN_ID)[-1]["filename"].endswith(".xlsx"))
        # запрошення майстра
        done = await confirm(await tool("invite_master", {"master_id": "oleg"}))
        self.assertIn("https://t.me/", done["message"])

    async def test_mcp_master_cannot_use_owner_tools(self):
        await self.link()
        tool, _ = await self.mcp_rpc(MASTER_ID)
        for name, args in (("get_shop", {}), ("set_price", {"service_id": "beard", "price": 1}),
                           ("set_client_ai", {"on": False}), ("export_bookings", {})):
            self.assertEqual((await tool(name, args))["error"], "owner_only", name)

    async def test_mcp_talks_to_bot_assistant(self):
        tool, confirm = await self.mcp_rpc()
        self.llm.add(tool_call(("set_price", {"service_id": "haircut", "price": 550})),
                     text_reply("Змінюю ціну стрижки на 550. Підтверджуєте?"))
        out = await tool("ask_bot_assistant", {"text": "стрижка тепер 550"})
        self.assertEqual(out["reply"], "Змінюю ціну стрижки на 550. Підтверджуєте?")
        await confirm(out)
        self.assertEqual(self.tenant.services["haircut"].price, 550)

    async def test_notifications_feed(self):
        h = await self.login()
        await self.call("POST", "api/push", h, {"endpoint": "https://push.example.com/abc"})
        self.web._push_all = self._no_push
        await self.app.notify_admins(self.tenant, "🆕 <b>Новий запис</b>\nІван, завтра 12:00")
        _, notes = await self.call("GET", "api/notes", h)
        self.assertEqual(notes["notes"][-1]["title"], "🆕 Новий запис")
        self.assertEqual(self.pushed, 1)

    pushed = 0

    async def _no_push(self, tenant, subs):
        self.pushed += len(subs)


class WebPushTests(unittest.TestCase):
    def test_rfc6979_vector_and_vapid(self):
        d = 0xC9AFA9D845BA75166B5C215767B1D6934E50C3DB36E89B127B8A622B120F6721
        sig = webpush.sign(d, b"sample")
        self.assertEqual(sig.hex().upper(),
                         "EFD48B2AACB6A8FD1140DD9CD45E81D69D2C877B56AAF991C34D0EA84EAF3716"
                         "F7CB1C942D657C41D436C7A1B6E29F65F3E900DBB9AFF4064DC4AB2F843ACDA8")
        self.assertTrue(webpush.verify(webpush.public_key(d), b"sample", sig))
        headers = webpush.vapid_headers(d, "https://fcm.googleapis.com/fcm/send/abc", "https://bot.example.com")
        self.assertTrue(headers["Authorization"].startswith("vapid t="))
        self.assertEqual(headers["Content-Length"], "0")


if __name__ == "__main__":
    unittest.main()
