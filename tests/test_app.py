"""Наскрізні сценарії бота: клієнт і власник у Telegram (фейковий Telegram і фейкова модель)."""

from __future__ import annotations

import re
import unittest
from datetime import datetime

from barberbot import clock
from barberbot.app import BotApp
from barberbot.db import DB
from barberbot.llm import LLMError
from barberbot.scheduler import Scheduler
from barberbot.telegram import TelegramError

from .helpers import (ADMIN_ID, CLIENT_ID, FakeLLM, FakeTelegram, cb, last_tool_result, make_settings, make_tenant,
                      msg, set_time, text_reply, tool_call)


class BotTestCase(unittest.IsolatedAsyncioTestCase):
    require_phone = True
    with_ai = True

    async def asyncSetUp(self):
        set_time(2026, 10, 26, 9, 0)  # понеділок
        self.tenant = make_tenant(require_phone=self.require_phone)
        self.slug = self.tenant.slug
        self.db = DB(":memory:")
        self.tg = FakeTelegram()
        self.llm = FakeLLM()
        self.settings = make_settings()
        self.app = BotApp(self.settings, [self.tenant], self.db, self.llm if self.with_ai else None,
                          api_factory=lambda t: self.tg)
        self.booking = self.app.bookings[self.slug]

    async def asyncTearDown(self):
        clock.set_fixed(None)
        self.db.close()

    async def send(self, update: dict) -> None:
        await self.app.handle_update(self.slug, update)

    def client(self, tg_id: int = CLIENT_ID):
        return self.db.get_client_by_tg(self.slug, tg_id)

    def make_client(self, phone: str | None = "+380501234567"):
        row = self.db.upsert_client(self.slug, CLIENT_ID, "Іван", None, "ivan", "uk", self.tenant.now())
        if phone:
            self.db.set_client_field(row["id"], "phone", phone)
        return self.db.get_client(row["id"])


class ClientButtonsTests(BotTestCase):
    async def test_start_and_info(self):
        await self.send(msg(text="/start"))
        start = self.tg.last(CLIENT_ID)
        self.assertIn("Тест Барбер", start["text"])
        keyboard = [b["text"] for row in start["reply_markup"]["keyboard"] for b in row]
        self.assertEqual(keyboard, ["📅 Записатися", "🗓 Мої записи", "💈 Послуги і ціни", "📍 Контакти"])

        await self.send(msg(text="💈 Послуги і ціни"))
        self.assertIn("Чоловіча стрижка</b> — 500 грн", self.tg.last(CLIENT_ID)["text"])
        await self.send(msg(text="📍 Контакти"))
        contacts = self.tg.last(CLIENT_ID)
        self.assertIn("вул. Тестова, 1", contacts["text"])
        self.assertIn("Пн–пт: 10:00–19:00", contacts["text"])
        self.assertEqual(self.tg.buttons(contacts)[0]["url"], "https://maps.example.com")
        await self.send(msg(text="/myid"))
        self.assertIn("<code>100</code>", self.tg.last(CLIENT_ID)["text"])
        await self.send(msg(text="/today"))  # не адмін
        self.assertIn("Не знаю такої команди", self.tg.last(CLIENT_ID)["text"])

    async def test_menu_in_russian_and_english(self):
        await self.send(msg(text="/start", lang="ru"))
        kb = self.tg.last(CLIENT_ID)["reply_markup"]["keyboard"]
        self.assertEqual(kb[0][0]["text"], "📅 Записаться")
        await self.send(msg(text="📅 Записаться", lang="ru"))
        self.assertEqual(self.tg.last(CLIENT_ID)["text"], "Выберите услугу:")
        await self.send(msg(text="📅 Book", lang="en"))
        self.assertEqual(self.tg.last(CLIENT_ID)["text"], "Choose a service:")

    async def test_full_booking_with_contact(self):
        await self.send(msg(text="📅 Записатися"))
        services = self.tg.last(CLIENT_ID)
        self.assertEqual([b["callback_data"] for b in self.tg.buttons(services)], ["bs:haircut", "bs:beard", "bs:combo"])

        await self.send(cb("bs:haircut"))
        masters = self.tg.last(CLIENT_ID)
        self.assertEqual(masters["message_id"], 777)  # той самий лист редагується
        datas = [b["callback_data"] for b in self.tg.buttons(masters)]
        self.assertEqual(datas, ["bm:haircut:andriy", "bm:haircut:oleg", "bm:haircut:any", "bs"])

        await self.send(cb("bm:haircut:any"))
        days = self.tg.buttons(self.tg.last(CLIENT_ID))
        self.assertEqual(days[0], {"text": "Сьогодні", "callback_data": "bd:haircut:any:20261026"})
        self.assertNotIn("bd:haircut:any:20261101", [b["callback_data"] for b in days])  # неділя

        await self.send(cb("bd:haircut:any:20261027"))
        times = self.tg.buttons(self.tg.last(CLIENT_ID))
        self.assertEqual(times[0]["callback_data"], "bt:haircut:any:20261027:1000")

        await self.send(cb("bt:haircut:any:20261027:1000"))
        card = self.tg.last(CLIENT_ID)
        self.assertIn("Перевірте", card["text"])
        self.assertIn("Завтра, вт 27.10", card["text"])
        confirm = self.tg.button(card, "bc:")["callback_data"]
        self.assertEqual(confirm, "bc:haircut:andriy:20261027:1000")

        await self.send(cb(confirm))
        ask = self.tg.last(CLIENT_ID)
        self.assertIn("номер телефону", ask["text"])
        self.assertTrue(ask["reply_markup"]["keyboard"][0][0]["request_contact"])
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 0)

        contact = {"phone_number": "380501234567", "first_name": "Іван", "user_id": CLIENT_ID}
        await self.send(msg(contact=contact))
        texts = self.tg.texts(CLIENT_ID)
        self.assertIn("Дякую, номер збережено 👍", texts)
        self.assertIn("Готово, ви записані", texts[-1])
        booking = self.db.one("SELECT * FROM bookings")
        self.assertEqual((booking["master_id"], booking["start_at"], booking["source"]),
                         ("andriy", "2026-10-27 10:00", "buttons"))
        self.assertEqual(self.client()["phone"], "+380501234567")
        admin = self.tg.last(ADMIN_ID)
        self.assertIn("Новий запис", admin["text"])
        self.assertIn("+380501234567", admin["text"])
        self.assertTrue(all(m != "answerCallbackQuery" or "text" not in p for m, p in self.tg.calls))

    async def test_typed_phone_and_abort(self):
        self.make_client(phone=None)
        await self.send(cb("bc:haircut:andriy:20261027:1000"))
        await self.send(msg(text="не скажу"))
        self.assertIn("Не схоже на номер", self.tg.last(CLIENT_ID)["text"])
        await self.send(msg(text="050 123 45 67"))
        self.assertEqual(self.client()["phone"], "0501234567")
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 1)

        self.db.set_client_field(self.client()["id"], "phone", None)
        await self.send(cb("bc:haircut:andriy:20261028:1000"))
        await self.send(msg(text="Скасувати"))
        self.assertIn("запис не створено", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 1)

    async def test_slot_taken_between_steps(self):
        self.make_client()
        other = self.db.upsert_client(self.slug, 999, "Інший", None, None, "uk", self.tenant.now())
        self.booking.create(other["id"], "haircut", "andriy", datetime(2026, 10, 26, 10, 0), "buttons")
        await self.send(cb("bc:haircut:andriy:20261026:1000"))
        last = self.tg.last(CLIENT_ID)
        self.assertIn("щойно зайняли", last["text"])
        self.assertNotIn("bt:haircut:andriy:20261026:1000", [b["callback_data"] for b in self.tg.buttons(last)])

    async def test_my_bookings_cancel_and_reschedule(self):
        client = self.make_client()
        b = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        await self.send(msg(text="🗓 Мої записи"))
        listing = self.tg.last(CLIENT_ID)
        self.assertIn("Завтра, вт 27.10 о 12:00", listing["text"])
        self.assertEqual([x["callback_data"] for x in self.tg.buttons(listing)], [f"rd:{b['id']}", f"cx:{b['id']}"])

        await self.send(cb(f"rd:{b['id']}"))
        await self.send(cb(f"rt:{b['id']}:20261028"))
        times = [x["callback_data"] for x in self.tg.buttons(self.tg.last(CLIENT_ID))]
        self.assertIn(f"rk:{b['id']}:20261028:1500", times)
        await self.send(cb(f"rk:{b['id']}:20261028:1500"))
        card = self.tg.last(CLIENT_ID)
        self.assertIn("Перенести запис?", card["text"])
        await self.send(cb(self.tg.button(card, "ry:")["callback_data"]))
        self.assertIn("Запис перенесено", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(self.db.get_booking(b["id"])["start_at"], "2026-10-28 15:00")
        self.assertIn("Перенесення", self.tg.last(ADMIN_ID)["text"])

        await self.send(cb(f"cx:{b['id']}"))
        self.assertIn("Скасувати запис?", self.tg.last(CLIENT_ID)["text"])
        await self.send(cb("cn"))
        self.assertEqual(self.db.get_booking(b["id"])["status"], "active")
        await self.send(cb(f"cy:{b['id']}"))
        self.assertIn("Запис скасовано", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(self.db.get_booking(b["id"])["status"], "cancelled")
        self.assertIn("Скасування", self.tg.last(ADMIN_ID)["text"])
        await self.send(cb(f"cy:{b['id']}"))
        self.assertIn("неактивний", self.tg.last(CLIENT_ID)["text"])

    async def test_expired_and_foreign_buttons(self):
        await self.send(cb("bs:nonexistent"))
        answer = self.tg.of("answerCallbackQuery")[-1]
        self.assertIn("неактуальна", answer["text"])
        await self.send(cb("bt:haircut:any:2026xx27:1000"))
        self.assertIn("неактуальна", self.tg.of("answerCallbackQuery")[-1]["text"])
        await self.send(cb("ans:1"))  # адмінська кнопка від клієнта
        self.assertEqual(self.tg.of("answerCallbackQuery")[-1]["text"], "Немає доступу")
        other = self.db.upsert_client(self.slug, 999, "Інший", None, None, "uk", self.tenant.now())
        foreign = self.booking.create(other["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        await self.send(cb(f"cy:{foreign['id']}"))
        self.assertEqual(self.db.get_booking(foreign["id"])["status"], "active")

    async def test_group_chats_are_ignored(self):
        update = msg(text="/start")
        update["message"]["chat"] = {"id": -100, "type": "group"}
        await self.send(update)
        self.assertEqual(self.tg.calls, [])


class AIChatTests(BotTestCase):
    def script_booking(self, day: str = "2026-10-27"):
        self.llm.add(
            tool_call(("get_free_slots", {"service_id": "haircut", "master_id": "any", "date": day})),
            lambda p: tool_call(("create_booking", {
                "service_id": "haircut", "master_id": "any", "date": day,
                "time": "12:00" if "12:00" in last_tool_result(p)["days"][0]["times"] else "13:00"})),
            text_reply("Є 12:00 у Андрія. Перевірте і натисніть «Підтвердити» 👇"),
        )

    async def test_ai_booking_confirmed_by_typing_yes(self):
        self.make_client()
        self.script_booking()
        await self.send(msg(text="Хочу на стрижку завтра о 12"))
        sent = self.tg.of("sendMessage", CLIENT_ID)
        self.assertEqual(sent[-2]["text"], "Є 12:00 у Андрія. Перевірте і натисніть «Підтвердити» 👇")
        self.assertNotIn("parse_mode", sent[-2])  # текст AI — без HTML
        self.assertEqual(self.tg.button(sent[-1], "ac:")["callback_data"], "ac:haircut:andriy:20261027:1200")
        self.assertTrue(self.tg.of("sendChatAction"))
        calls_before = len(self.llm.payloads)

        card_id = self.tg.of("sendMessage", CLIENT_ID)[-1] and self.tg.next_id
        await self.send(msg(text="Так, дякую"))
        self.assertEqual(len(self.llm.payloads), calls_before)  # модель не викликалась
        booked = self.tg.last(CLIENT_ID)
        self.assertIn("Готово, ви записані", booked["text"])
        self.assertEqual(booked.get("message_id"), card_id)  # картка перетворилась на підтвердження
        booking = self.db.one("SELECT * FROM bookings")
        self.assertEqual((booking["source"], booking["start_at"]), ("ai", "2026-10-27 12:00"))
        self.assertIn("через AI-чат", self.tg.last(ADMIN_ID)["text"])
        # подія для контексту AI
        notes = [r["content"] for r in self.db.q("SELECT content FROM history WHERE role='user'")]
        self.assertTrue(any("Клієнт підтвердив запис" in n for n in notes))

    async def test_other_text_cancels_pending_confirmation(self):
        self.make_client()
        self.script_booking()
        await self.send(msg(text="Хочу на стрижку завтра о 12"))
        self.llm.add(text_reply("Можу запропонувати 13:00."))
        await self.send(msg(text="А можна трохи пізніше?"))
        self.llm.add(text_reply("Добре!"))
        await self.send(msg(text="так"))  # стара картка вже не підтверджується текстом
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 0)
        await self.send(cb("pn"))
        self.assertIn("Напишіть, що змінити", self.tg.last(CLIENT_ID)["text"])

    async def test_ai_card_button_asks_phone_then_books(self):
        self.make_client(phone=None)
        self.script_booking()
        await self.send(msg(text="Запишіть на завтра о 12"))
        data = self.tg.button(self.tg.of("sendMessage", CLIENT_ID)[-1], "ac:")["callback_data"]
        await self.send(cb(data))
        self.assertIn("номер телефону", self.tg.last(CLIENT_ID)["text"])
        await self.send(msg(contact={"phone_number": "+36301234567", "user_id": CLIENT_ID}))
        self.assertEqual(self.db.one("SELECT source FROM bookings")["source"], "ai")

    async def test_handoff_relay_and_resume(self):
        self.make_client()
        self.llm.add(
            tool_call(("handoff_to_owner", {"reason": "Просить знижку", "summary": "Хоче -20%"})),
            text_reply("Передав питання адміністратору — він відповість тут."),
        )
        await self.send(msg(text="Дайте знижку 20%"))
        self.assertEqual(self.tg.last(CLIENT_ID)["text"], "Передав питання адміністратору — він відповість тут.")
        handoff = self.tg.last(ADMIN_ID)
        self.assertIn("Потрібна ваша відповідь", handoff["text"])
        self.assertIn("Хоче -20%", handoff["text"])
        self.assertIn("— Клієнт: Дайте знижку 20%", handoff["text"])
        client_id = self.client()["id"]
        self.assertEqual([b["callback_data"] for b in self.tg.buttons(handoff)], [f"ar:{client_id}", f"aR:{client_id}"])
        self.assertIsNotNone(self.client()["paused_until"])

        calls = len(self.llm.payloads)
        await self.send(msg(text="Ну що там?"))
        self.assertEqual(len(self.llm.payloads), calls)
        self.assertIn("Ну що там?", self.tg.last(ADMIN_ID)["text"])

        handoff_id = self.tg.of("sendMessage", ADMIN_ID)[0]
        sent_ids = [p for m, p in self.tg.calls if m == "sendMessage" and p["chat_id"] == ADMIN_ID]
        self.assertTrue(sent_ids)
        relay_msg_id = self.db.one("SELECT admin_msg_id FROM relay ORDER BY admin_msg_id")["admin_msg_id"]
        await self.send(msg(uid=ADMIN_ID, text="Привіт! Знижок, на жаль, немає 🙂",
                            reply_to_message={"message_id": relay_msg_id}))
        to_client = self.tg.last(CLIENT_ID)
        self.assertIn("<b>Адміністратор:</b>\nПривіт! Знижок, на жаль, немає 🙂", to_client["text"])
        self.assertIn("Надіслано", self.tg.last(ADMIN_ID)["text"])
        self.assertTrue(handoff_id)

        await self.send(cb(f"ar:{client_id}", uid=ADMIN_ID))
        self.assertIn("Напишіть відповідь", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="Чекаємо вас!"))
        self.assertIn("Чекаємо вас!", self.tg.last(CLIENT_ID)["text"])

        await self.send(cb(f"aR:{client_id}", uid=ADMIN_ID))
        self.assertIsNone(self.client()["paused_until"])
        self.llm.add(text_reply("Звісно! Чим допомогти?"))
        await self.send(msg(text="Ок, тоді просто запишіть"))
        self.assertEqual(self.tg.last(CLIENT_ID)["text"], "Звісно! Чим допомогти?")
        # AI бачить, що відповідав адміністратор
        last_payload = self.llm.payloads[-1]
        joined = str(last_payload["messages"])
        self.assertIn("Адміністратор написав клієнту", joined)

    async def test_photo_goes_to_owner(self):
        self.make_client()
        await self.send(msg(photo=[{"file_id": "x", "width": 1, "height": 1}], caption="оплата"))
        self.assertIn("Передаю адміністратору", self.tg.last(CLIENT_ID)["text"])
        self.assertIn("фото або файл", self.tg.of("sendMessage", ADMIN_ID)[0]["text"])
        self.assertEqual(self.tg.of("copyMessage")[0]["chat_id"], ADMIN_ID)
        self.assertEqual(self.llm.payloads, [])

    async def test_voice_and_sticker(self):
        await self.send(msg(voice={"file_id": "v"}))
        self.assertIn("Голосові", self.tg.last(CLIENT_ID)["text"])
        await self.send(msg(sticker={"file_id": "s"}))
        self.assertIn("лише текстові", self.tg.last(CLIENT_ID)["text"])

    async def test_ai_error_and_alert(self):
        self.make_client()
        self.llm.add(LLMError("HTTP 401: invalid x-api-key", 401))
        await self.send(msg(text="Привіт"))
        self.assertIn("не можу відповісти", self.tg.last(CLIENT_ID)["text"])
        self.assertIn("AI не відповідає", self.tg.last(ADMIN_ID)["text"])
        self.llm.add(LLMError("HTTP 401: invalid x-api-key", 401))
        admin_msgs = len(self.tg.of("sendMessage", ADMIN_ID))
        await self.send(msg(text="Алло"))
        self.assertEqual(len(self.tg.of("sendMessage", ADMIN_ID)), admin_msgs)  # не частіше разу на годину

    async def test_rate_limit(self):
        self.make_client()
        for i in range(5):
            self.llm.add(text_reply(f"Відповідь {i}"))
            await self.send(msg(text=f"Питання {i}"))
        await self.send(msg(text="Ще одне"))
        self.assertIn("Забагато повідомлень", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(len(self.llm.payloads), 5)

    async def test_daily_token_budget(self):
        self.make_client()
        self.settings.daily_token_limit = 1000
        self.llm.add(text_reply("Перша відповідь"))
        await self.send(msg(text="Привіт"))
        await self.send(msg(text="Ще питання"))
        self.assertIn("Оберіть дію в меню", self.tg.last(CLIENT_ID)["text"])
        self.assertIn("ліміт AI вичерпано", self.tg.last(ADMIN_ID)["text"])

    async def test_global_pause(self):
        self.make_client()
        await self.send(msg(uid=ADMIN_ID, text="/pause"))
        self.assertIn("AI вимкнено", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(text="Є хтось?"))
        await self.send(msg(text="Алло"))
        acks = [t for t in self.tg.texts(CLIENT_ID) if "Адміністратор відповість" in t]
        self.assertEqual(len(acks), 1)
        self.assertIn("Алло", self.tg.last(ADMIN_ID)["text"])
        self.assertEqual(self.llm.payloads, [])
        await self.send(msg(uid=ADMIN_ID, text="/resume"))
        self.llm.add(text_reply("Так, я тут!"))
        await self.send(msg(text="Є хтось?"))
        self.assertEqual(self.tg.last(CLIENT_ID)["text"], "Так, я тут!")


class NoAITests(BotTestCase):
    with_ai = False

    async def test_buttons_only_mode(self):
        await self.send(msg(text="/start"))
        self.assertIn("Оберіть дію в меню", self.tg.last(CLIENT_ID)["text"])
        await self.send(msg(text="Скільки коштує стрижка?"))
        self.assertIn("Оберіть дію в меню", self.tg.last(CLIENT_ID)["text"])


class AdminTests(BotTestCase):
    async def test_admin_panel(self):
        client = self.make_client()
        b1 = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 26, 12, 0), "ai")
        await self.send(msg(uid=ADMIN_ID, text="/start"))
        self.assertIn("/admin", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="/admin"))
        self.assertIn("Панель керування", self.tg.last(ADMIN_ID)["text"])
        self.assertIn("✅ увімкнено", self.tg.last(ADMIN_ID)["text"])

        await self.send(msg(uid=ADMIN_ID, text="/today"))
        today = self.tg.last(ADMIN_ID)
        self.assertIn("12:00–13:00", today["text"])
        self.assertIn("🤖", today["text"])
        self.assertEqual([x["callback_data"] for x in self.tg.buttons(today)], [f"ans:{b1['id']}", f"acx:{b1['id']}"])
        await self.send(msg(uid=ADMIN_ID, text="/tomorrow"))
        self.assertIn("записів немає", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="/week"))
        self.assertIn("Чоловіча стрижка", self.tg.last(ADMIN_ID)["text"])

        await self.send(cb(f"ans:{b1['id']}", uid=ADMIN_ID))
        self.assertEqual(self.db.get_booking(b1["id"])["status"], "no_show")
        self.assertIn("не прийшов", self.tg.of("answerCallbackQuery")[-1]["text"])

        await self.send(msg(uid=ADMIN_ID, text="/stats"))
        stats = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Статистика за 30 днів", stats)
        self.assertIn("не прийшли: 1", stats)

    async def test_week_mentions_later_bookings_and_all_lists_them(self):
        # Клієнт може записатися на 14 днів уперед, а /week показує лише 7 — запис через 13 днів не губиться.
        client = self.make_client()
        cancelled = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 11, 5, 12, 0), "buttons")
        self.booking.cancel(cancelled["id"], "client")
        self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        far = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 11, 6, 12, 0), "buttons")

        await self.send(msg(uid=ADMIN_ID, text="/week"))
        week = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("27.10", week)
        self.assertNotIn("06.11", week)
        self.assertIn("Пізніше ще записів: 1 — /all", week)

        await self.send(msg(uid=ADMIN_ID, text="/all"))
        upcoming = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Усі майбутні записи", upcoming)
        self.assertIn("27.10", upcoming)
        self.assertIn("06.11", upcoming)
        # Дійсні — пронумеровані по днях, скасовані — окремим блоком унизу.
        self.assertIn("<b>1. 12:00–13:00</b>", upcoming)
        self.assertIn("<b>2. 12:00–13:00</b>", upcoming)
        active_part, cancelled_part = upcoming.split("❌ <b>Скасовані</b> — 1")
        self.assertIn("06.11", active_part)
        self.assertNotIn("05.11", active_part)
        self.assertIn("Чт, 05.11 12:00 · Андрій · Чоловіча стрижка · Іван — скасував клієнт", cancelled_part)
        self.assertNotIn("Скасовані", week)  # /week — лише робочий розклад
        self.assertEqual(self.db.get_booking(far["id"])["status"], "active")

    async def test_admin_cancel_notifies_client(self):
        client = self.make_client()
        b = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        await self.send(cb(f"acx:{b['id']}", uid=ADMIN_ID))
        ask = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Скасувати цей запис?", ask)
        self.assertIn("<b>Завтра, вт 27.10, 12:00–13:00</b> · Андрій", ask)
        self.assertIn("Клієнт отримає повідомлення", ask)
        await self.send(cb(f"acy:{b['id']}", uid=ADMIN_ID))
        self.assertEqual(self.db.get_booking(b["id"])["status"], "cancelled")
        self.assertIn("скасовано адміністратором", self.tg.last(CLIENT_ID)["text"])

    async def test_block_commands(self):
        client = self.make_client()
        self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 27, 14, 0), "buttons")
        await self.send(msg(uid=ADMIN_ID, text="/block"))
        self.assertIn("Формат", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="/block andriy 27.10 13:00-16:00 запис по телефону"))
        done = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Закрито: Андрій", done)
        self.assertIn("13:00–16:00", done)
        self.assertIn("уже є записи", done)
        slots = self.booking.free_slots("haircut", "andriy", datetime(2026, 10, 27).date())
        self.assertNotIn("13:00", slots)
        self.assertIn("16:00", slots)
        await self.send(msg(uid=ADMIN_ID, text="/block всі 31.10"))
        self.assertEqual(self.booking.free_slots("haircut", "any", datetime(2026, 10, 31).date()), {})
        await self.send(msg(uid=ADMIN_ID, text="/block петро 31.10"))
        self.assertIn("Не зрозумів", self.tg.last(ADMIN_ID)["text"])

        await self.send(msg(uid=ADMIN_ID, text="/blocks"))
        buttons = self.tg.buttons(self.tg.last(ADMIN_ID))
        self.assertEqual(len(buttons), 2)
        await self.send(cb(buttons[1]["callback_data"], uid=ADMIN_ID))
        self.assertTrue(self.booking.free_slots("haircut", "any", datetime(2026, 10, 31).date()))

    async def test_reload(self):
        path = self.tenant.path
        path.write_text(path.read_text(encoding="utf-8").replace("price = 500", "price = 550"), encoding="utf-8")
        await self.send(msg(uid=ADMIN_ID, text="/reload"))
        self.assertIn("Налаштування оновлено", self.tg.last(ADMIN_ID)["text"])
        self.assertEqual(self.app.tenants[self.slug].services["haircut"].price, 550)
        path.write_text("name = ", encoding="utf-8")
        await self.send(msg(uid=ADMIN_ID, text="/reload"))
        self.assertIn("помилка", self.tg.last(ADMIN_ID)["text"])
        self.assertEqual(self.app.tenants[self.slug].services["haircut"].price, 550)

    async def test_blocked_client_marked(self):
        client = self.make_client()
        self.tg.fail["sendMessage"] = TelegramError(403, "Forbidden: bot was blocked by the user")
        await self.app.send(self.tenant, CLIENT_ID, "test")
        self.assertEqual(self.db.get_client(client["id"])["blocked"], 1)


class SchedulerTests(BotTestCase):
    async def test_reminders(self):
        client = self.make_client()
        b = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 27, 10, 0), "buttons")
        late = self.booking.create(client["id"], "beard", "oleg", datetime(2026, 10, 27, 15, 0), "buttons")
        self.db.conn.execute("UPDATE bookings SET created_at = '2026-10-26 16:00' WHERE id = ?", (late["id"],))
        sched = Scheduler(self.app)

        set_time(2026, 10, 26, 9, 30)
        await sched.tick_all()
        self.assertEqual(self.tg.of("sendMessage", CLIENT_ID), [])

        set_time(2026, 10, 26, 10, 0)
        await sched.tick_all()
        await sched.tick_all()
        reminders = self.tg.of("sendMessage", CLIENT_ID)
        self.assertEqual(len(reminders), 1)
        self.assertIn("Нагадування про візит", reminders[0]["text"])
        self.assertIn("Завтра, вт 27.10 о 10:00", reminders[0]["text"])
        self.assertEqual([x["callback_data"] for x in self.tg.buttons(reminders[0])],
                         [f"ok:{b['id']}", f"rd:{b['id']}", f"cx:{b['id']}"])

        set_time(2026, 10, 26, 16, 0)  # 24 год до другого запису минули, але він створений пізніше
        await sched.tick_all()
        self.assertEqual(len(self.tg.of("sendMessage", CLIENT_ID)), 1)

        set_time(2026, 10, 27, 8, 0)
        await sched.tick_all()
        self.assertEqual(len(self.tg.of("sendMessage", CLIENT_ID)), 2)
        set_time(2026, 10, 27, 13, 0)
        await sched.tick_all()
        texts = [p["text"] for p in self.tg.of("sendMessage", CLIENT_ID)]
        self.assertEqual(len(texts), 3)
        self.assertIn("15:00", texts[-1])

        await self.send(cb(f"ok:{b['id']}"))
        self.assertIn("Чудово, чекаємо!", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(self.db.get_booking(b["id"])["client_confirmed"], 1)

    async def test_nudge_and_digest(self):
        set_time(2026, 9, 28, 9, 0)
        client = self.make_client()
        self.booking.create(client["id"], "haircut", "oleg", datetime(2026, 9, 29, 10, 0), "buttons")
        sched = Scheduler(self.app)

        set_time(2026, 10, 27, 10, 30)  # ще рано (11:00)
        await sched.nudges(self.slug)
        self.assertEqual(self.tg.of("sendMessage", CLIENT_ID), [])
        set_time(2026, 10, 27, 11, 5)
        await sched.nudges(self.slug)
        await sched.nudges(self.slug)
        nudges = self.tg.of("sendMessage", CLIENT_ID)
        self.assertEqual(len(nudges), 1)
        self.assertIn("Минуло вже 4 тиж.", nudges[0]["text"])
        await self.send(cb(self.tg.buttons(nudges[0])[0]["callback_data"]))
        self.assertIn("Оберіть день", self.tg.last(CLIENT_ID)["text"])
        await self.send(cb("noff"))
        self.assertEqual(self.client()["no_nudges"], 1)

        set_time(2026, 10, 28, 13, 0)  # поза вікном ранкового зведення
        await sched.digest(self.slug)
        self.assertNotIn("Доброго ранку", " ".join(self.tg.texts(ADMIN_ID)))
        set_time(2026, 10, 29, 9, 1)
        await sched.digest(self.slug)
        await sched.digest(self.slug)
        digests = [t for t in self.tg.texts(ADMIN_ID) if "Доброго ранку" in t]
        self.assertEqual(len(digests), 1)


if __name__ == "__main__":
    unittest.main()


class AdminBookingTests(BotTestCase):
    async def book(self, text_or_contact, service="haircut", master="andriy", day="20261027", time_="1200"):
        """Адмін проходить /book до картки підтвердження."""
        await self.send(msg(uid=ADMIN_ID, text="/book"))
        self.assertIn("Запис клієнта", self.tg.last(ADMIN_ID)["text"])
        await self.send(cb(f"aBs:{service}", uid=ADMIN_ID))
        await self.send(cb(f"aBm:{service}:{master}", uid=ADMIN_ID))
        await self.send(cb(f"aBd:{service}:{master}:{day}", uid=ADMIN_ID))
        await self.send(cb(f"aBt:{service}:{master}:{day}:{time_}", uid=ADMIN_ID))
        self.assertIn("Надішліть дані клієнта", self.tg.last(ADMIN_ID)["text"])
        if isinstance(text_or_contact, dict):
            await self.send(msg(uid=ADMIN_ID, contact=text_or_contact))
        else:
            await self.send(msg(uid=ADMIN_ID, text=text_or_contact))
        return self.tg.last(ADMIN_ID)

    async def test_offline_client_with_note(self):
        card = await self.book("Олена Петрівна +380671234567\nхоче коротше, ніж минулого разу")
        self.assertIn("Олена Петрівна · +380671234567", card["text"])
        self.assertIn("📝 хоче коротше", card["text"])
        self.assertIn("Новий клієнт без Telegram", card["text"])
        self.assertEqual([b["callback_data"] for b in self.tg.buttons(card)], ["aBy", "aBx"])

        await self.send(cb("aBy", uid=ADMIN_ID))
        b = self.db.q("SELECT * FROM bookings")[0]
        self.assertEqual((b["source"], b["status"], b["start_at"]), ("admin", "active", "2026-10-27 12:00"))
        self.assertEqual(b["note"], "хоче коротше, ніж минулого разу")
        client = self.db.get_client(b["client_id"])
        self.assertLess(client["tg_id"], 0)
        self.assertEqual((client["name"], client["phone"]), ("Олена Петрівна", "+380671234567"))
        done = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Записано", done)
        self.assertIn("немає в Telegram", done)
        self.assertEqual([p for m, p in self.tg.calls if m == "sendMessage" and p["chat_id"] < 0], [])

        set_time(2026, 10, 27, 9, 0)
        await self.send(msg(uid=ADMIN_ID, text="/today"))
        today = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("Олена Петрівна", today)
        self.assertIn("📞", today)
        self.assertIn("📝 хоче коротше", today)

        # Скасування: адміну чесно кажемо, що клієнт повідомлення не отримав.
        await self.send(cb(f"acy:{b['id']}", uid=ADMIN_ID))
        self.assertIn("немає в Telegram", self.tg.last(ADMIN_ID)["text"])
        self.assertEqual(self.db.get_booking(b["id"])["status"], "cancelled")

    async def test_existing_telegram_client_found_by_phone_is_notified(self):
        client = self.make_client(phone="+380501234567")
        card = await self.book("Іван +38050 123 45 67")
        self.assertIn("уже є в боті", card["text"])
        await self.send(cb("aBy", uid=ADMIN_ID))
        b = self.db.q("SELECT * FROM bookings")[0]
        self.assertEqual(b["client_id"], client["id"])
        self.assertIn("Адміністратор записав вас", self.tg.last(CLIENT_ID)["text"])
        self.assertIn("надіслано", self.tg.last(ADMIN_ID)["text"])
        # Записане адміном видно клієнту в «Мої записи».
        await self.send(msg(text="🗓 Мої записи"))
        self.assertIn("Чоловіча стрижка", self.tg.last(CLIENT_ID)["text"])

    async def test_shared_telegram_contact(self):
        await self.book({"phone_number": "380931112233", "first_name": "Марко", "user_id": 777})
        await self.send(cb("aBy", uid=ADMIN_ID))
        client = self.db.get_client_by_tg(self.slug, 777)
        self.assertEqual((client["name"], client["phone"]), ("Марко", "+380931112233"))
        self.assertIn("Адміністратор записав вас", self.tg.last(777)["text"])

    async def test_admin_ignores_client_limits_but_not_busy_time(self):
        set_time(2026, 10, 26, 10, 20)
        client = self.make_client()
        for start in (datetime(2026, 10, 27, 12, 0), datetime(2026, 10, 28, 12, 0)):
            self.booking.create(client["id"], "haircut", "andriy", start, "buttons")
        # Клієнт сам більше записатися не може (ліміт 2), а для адміна часу «за годину» не треба чекати.
        await self.send(msg(uid=ADMIN_ID, text="/book"))
        await self.send(cb("aBd:haircut:andriy:20261026", uid=ADMIN_ID))
        times = [b["text"] for b in self.tg.buttons(self.tg.last(ADMIN_ID))]
        self.assertIn("10:30", times)
        await self.send(cb("aBt:haircut:andriy:20261026:1030", uid=ADMIN_ID))
        await self.send(msg(uid=ADMIN_ID, text="Іван +380501234567"))
        await self.send(cb("aBy", uid=ADMIN_ID))
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings WHERE status = 'active'"), 3)
        # Зайнятий час адмін не отримає.
        await self.send(cb("aBd:haircut:andriy:20261027", uid=ADMIN_ID))
        self.assertNotIn("12:00", [b["text"] for b in self.tg.buttons(self.tg.last(ADMIN_ID))])

    async def test_card_requires_name_and_cancel_clears_state(self):
        await self.book("+380671234567")
        self.assertIn("Не бачу імені", self.tg.last(ADMIN_ID)["text"])
        await self.send(cb("aBx", uid=ADMIN_ID))
        self.assertIn("Запис не створено", self.tg.last(ADMIN_ID)["text"])
        await self.send(cb("aBy", uid=ADMIN_ID))  # стара кнопка
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 0)

    async def test_client_cannot_use_admin_booking(self):
        await self.send(cb("aBs:haircut"))
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 0)
        self.assertNotIn("Оберіть майстра", self.tg.last(CLIENT_ID).get("text", ""))

    async def test_all_has_cancel_buttons_and_notifies_client(self):
        client = self.make_client()
        b = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 11, 6, 12, 0), "buttons")
        await self.send(msg(uid=ADMIN_ID, text="/all"))
        upcoming = self.tg.last(ADMIN_ID)
        self.assertIn(f"acx:{b['id']}", [x["callback_data"] for x in self.tg.buttons(upcoming)])
        await self.send(cb(f"acx:{b['id']}", uid=ADMIN_ID))
        await self.send(cb(f"acy:{b['id']}", uid=ADMIN_ID))
        self.assertEqual(self.db.get_booking(b["id"])["status"], "cancelled")
        self.assertIn("скасовано адміністратором", self.tg.last(CLIENT_ID)["text"])
        self.assertIn("Клієнта повідомлено", self.tg.last(ADMIN_ID)["text"])


class ParseClientInfoTests(unittest.TestCase):
    def test_variants(self):
        from barberbot.app import parse_client_info
        self.assertEqual(parse_client_info("Олена +380671234567\nкоротше\nбез укладання"),
                         ("Олена", "+380671234567", "коротше; без укладання"))
        self.assertEqual(parse_client_info("+38 (067) 123-45-67\nОлена"), ("Олена", "+380671234567", ""))
        self.assertEqual(parse_client_info("Олена, 0671234567"), ("Олена", "0671234567", ""))
        self.assertEqual(parse_client_info("Олена"), ("Олена", None, ""))
        self.assertEqual(parse_client_info("  "), ("", None, ""))


class AddonTests(BotTestCase):
    """Додаткові послуги (миття голови) на справжньому демо-закладі."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        from pathlib import Path
        import tempfile
        from barberbot.config import load_tenant
        from .helpers import TOKEN
        root = Path(__file__).resolve().parent.parent
        text = (root / "config/tenants/demo-barbershop.toml").read_text(encoding="utf-8")
        # Справжні токен і адміни (на сервері) підміняємо тестовими.
        text = re.sub(r'(?m)^bot_token = ".*"$', f'bot_token = "{TOKEN}"', text)
        text = re.sub(r"(?m)^admins = \[.*\]$", f"admins = [{ADMIN_ID}]", text)
        path = Path(tempfile.mkdtemp()) / "demo-barbershop.toml"
        path.write_text(text, encoding="utf-8")
        self.tenant = load_tenant(path)
        self.slug = self.tenant.slug
        self.app = BotApp(self.settings, [self.tenant], self.db, None, api_factory=lambda t: self.tg)
        self.booking = self.app.bookings[self.slug]
        self.make_client()

    def card_buttons(self):
        return {b["callback_data"]: b["text"] for b in self.tg.buttons(self.tg.last(CLIENT_ID))}

    async def test_wash_addon(self):
        await self.send(cb("bt:women_long:olena:20261027:1200"))
        self.assertEqual(self.card_buttons().get("ba:women_long+wash:olena:20261027:1200"),
                         "➕ Миття голови (+15 хв, +150 грн)")
        await self.send(cb("ba:women_long+wash:olena:20261027:1200"))
        card = self.tg.last(CLIENT_ID)["text"]
        self.assertIn("Жіноча стрижка (довге волосся) + Миття голови", card)
        self.assertIn("105 хв", card)
        self.assertIn(self.tenant.price_str(1100), card)
        await self.send(cb("bc:women_long+wash:olena:20261027:1200"))
        b = self.db.q("SELECT * FROM bookings")[0]
        self.assertEqual((b["service_title"], b["end_at"], b["price"]),
                         ("Жіноча стрижка (довге волосся) + Миття голови", "2026-10-27 13:45", 1100))
        self.assertTrue(self.tg.last(CLIENT_ID)["text"].startswith("✅ <b>Готово, ви записані!</b>"))

    async def test_wash_where_allowed(self):
        await self.send(cb("bt:haircut:oleg:20261027:1200"))
        self.assertEqual([d.split(":")[1] for d in self.card_buttons() if d.startswith("ba:")], ["haircut+wash"])
        for data in ("bt:trim_ends:olena:20261027:1200", "bt:beard:andriy:20261027:1200"):
            await self.send(cb(data))
            self.assertFalse([d for d in self.card_buttons() if d.startswith("ba:")], data)

    async def test_wash_hidden_from_lists_and_shown_in_prices(self):
        await self.send(msg(text="📅 Записатися"))
        services = list(self.card_buttons())
        self.assertNotIn("bs:wash", services)
        self.assertFalse([d for d in services if "+" in d])
        await self.send(msg(text="💈 Послуги і ціни"))
        prices = self.tg.last(CLIENT_ID)["text"]
        self.assertIn("Можна додати до стрижки", prices)
        self.assertIn("Миття голови — +150 грн, +15 хв", prices)
        self.assertNotIn("Чоловіча стрижка + Миття голови", prices)
        self.assertNotIn("Миття і укладання входять", prices)

    async def test_addon_needs_time_for_both(self):
        # Олег зайнятий з 13:00 — о 12:00 стрижка (60 хв) влазить, а стрижка + миття (75 хв) — ні.
        other = self.db.upsert_client(self.slug, 999, "Інший", None, None, "uk", self.tenant.now())
        self.booking.create(other["id"], "beard", "oleg", datetime(2026, 10, 27, 13, 0), "buttons")
        await self.send(cb("bt:haircut+wash:oleg:20261027:1200"))
        self.assertIn("щойно зайняли", self.tg.last(CLIENT_ID)["text"])
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings WHERE client_id = ?", self.client()["id"]), 0)

    async def test_service_list_grouped(self):
        await self.send(msg(text="📅 Записатися"))
        rows = [b["text"] for b in self.tg.buttons(self.tg.last(CLIENT_ID))]
        self.assertEqual(rows[0], "━━ 👨 Чоловічі ━━")
        women, kids = rows.index("━━ 👩 Жіночі ━━"), rows.index("━━ 🧒 Дитячі (до 8 років) ━━")
        self.assertIn("Чоловіча стрижка · 600 грн", rows[1:women])
        self.assertIn("Стрижка чубчика · 200 грн", rows[women:kids])
        self.assertEqual(rows[kids + 1:], ["Дитяча стрижка для хлопчика (до 8 років) · 400 грн",
                                           "Дитяча стрижка для дівчинки (до 8 років) · 500 грн"])
        # Заголовок — не кнопка дії: нічого не відбувається і без «кнопка застаріла».
        calls = len(self.tg.calls)
        await self.send(cb("noop"))
        self.assertEqual([m for m, _ in self.tg.calls[calls:]], ["answerCallbackQuery"])
        self.assertIsNone(self.tg.calls[-1][1].get("text"))

    async def test_prices_grouped(self):
        await self.send(msg(text="💈 Послуги і ціни"))
        text = self.tg.last(CLIENT_ID)["text"]
        men, women, kids = (text.index(f"<b>{g}</b>") for g in ("👨 Чоловічі", "👩 Жіночі", "🧒 Дитячі (до 8 років)"))
        self.assertLess(men, text.index("Стрижка машинкою"))
        self.assertLess(text.index("Стрижка машинкою"), women)
        self.assertLess(women, text.index("Стрижка чубчика"))
        self.assertLess(text.index("Стрижка чубчика"), kids)
        self.assertLess(kids, text.index("для дівчинки"))
        self.assertEqual(text.count("━━━━━━━━━━━━"), 3)

    async def test_admin_book_list_grouped(self):
        await self.send(msg(uid=ADMIN_ID, text="/book"))
        rows = [(b["text"], b["callback_data"]) for b in self.tg.buttons(self.tg.last(ADMIN_ID))]
        self.assertEqual(rows[0], ("━━ 👨 Чоловічі ━━", "noop"))
        self.assertIn(("Дитяча стрижка для дівчинки (до 8 років) · 500 грн", "aBs:kids_girl"), rows)

    async def test_addon_button_rejects_plain_service(self):
        await self.send(cb("ba:haircut:oleg:20261027:1200"))  # не комбінація — застаріла кнопка
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 0)



class AdminListTests(BotTestCase):
    """Списки записів для адміна: нумерація, кнопки з номером, скасовані внизу, очищення."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ivan = self.make_client()
        self.olena = self.db.create_offline_client(self.slug, "Олена", "+380671234567", self.tenant.now())
        self.b1 = self.booking.create(self.ivan["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        self.b2 = self.booking.create(self.olena["id"], "haircut", "andriy", datetime(2026, 10, 27, 14, 0), "admin")
        self.b3 = self.booking.create(self.ivan["id"], "haircut", "andriy", datetime(2026, 11, 3, 10, 0), "buttons")
        self.booking.cancel(self.b3["id"], "client")

    def buttons(self):
        return [(b["text"], b["callback_data"]) for b in self.tg.buttons(self.tg.last(ADMIN_ID))]

    async def test_all_numbers_match_buttons(self):
        await self.send(msg(uid=ADMIN_ID, text="/all"))
        text = self.tg.last(ADMIN_ID)["text"]
        self.assertLess(text.index("<b>1. 12:00–13:00</b>"), text.index("<b>2. 14:00–15:00</b>"))
        self.assertLess(text.index("👤 Олена"), text.index("❌ <b>Скасовані</b>"))
        self.assertEqual(self.buttons(), [
            ("🗑 1 · вт 27.10 12:00 · Іван", f"acx:{self.b1['id']}"),
            ("🗑 2 · вт 27.10 14:00 · Олена", f"acx:{self.b2['id']}"),
            ("🧹 Прибрати скасовані (1)", "aCc"),
        ])

    async def test_today_buttons_numbered(self):
        set_time(2026, 10, 27, 9, 0)
        await self.send(msg(uid=ADMIN_ID, text="/today"))
        text = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("<b>1. 12:00–13:00</b>", text)
        self.assertIn("<b>2. 14:00–15:00</b>", text)
        self.assertEqual(self.buttons(), [
            ("🚫 1 не прийшов", f"ans:{self.b1['id']}"), ("🗑 1 скасувати", f"acx:{self.b1['id']}"),
            ("🚫 2 не прийшов", f"ans:{self.b2['id']}"), ("🗑 2 скасувати", f"acx:{self.b2['id']}"),
        ])

    async def test_cancel_offline_client_is_explained_upfront(self):
        await self.send(cb(f"acx:{self.b2['id']}", uid=ADMIN_ID))
        ask = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("👤 Олена · +380671234567", ask)
        self.assertIn("Клієнта немає в Telegram", ask)

    async def test_clear_cancelled(self):
        await self.send(cb("aCc", uid=ADMIN_ID))
        self.assertIn("Прибрати скасовані записи зі списку (1)?", self.tg.last(ADMIN_ID)["text"])
        await self.send(cb("aCy", uid=ADMIN_ID))
        self.assertIn("Прибрано скасованих записів: 1", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="/all"))
        self.assertNotIn("Скасовані", self.tg.last(ADMIN_ID)["text"])
        self.assertNotIn("aCc", [d for _, d in self.buttons()])
        # Запис лишився в базі як скасований — статистика не змінюється.
        self.assertEqual(self.db.get_booking(self.b3["id"])["status"], "cancelled")
        await self.send(msg(uid=ADMIN_ID, text="/stats"))
        self.assertIn("скасовано: 1", self.tg.last(ADMIN_ID)["text"])

    async def test_new_cancellation_shows_again_after_clear(self):
        self.db.clear_cancelled(self.slug, datetime(2026, 10, 26))
        self.booking.cancel(self.b1["id"], "admin")
        await self.send(msg(uid=ADMIN_ID, text="/all"))
        text = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("❌ <b>Скасовані</b> — 1", text)
        self.assertIn("Іван — скасував адмін", text)
        self.assertIn("<b>1. 14:00–15:00</b>", text)  # нумерація лише по дійсних
