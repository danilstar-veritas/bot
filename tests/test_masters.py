"""Майстри в боті: підключення за посиланням, свій день, неявка, закритий час, сповіщення."""

from __future__ import annotations

import re
import unittest
from datetime import date, datetime

from barberbot.scheduler import Scheduler

from .helpers import ADMIN_ID, CLIENT_ID, cb, msg, set_time, text_reply
from .test_app import BotTestCase

MASTER_ID = 300


class MasterTestCase(BotTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ivan = self.make_client()
        self.olena = self.db.create_offline_client(self.slug, "Олена", "+380671234567", self.tenant.now())
        self.b_andriy = self.booking.create(self.ivan["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0),
                                            "buttons")
        self.b_oleg = self.booking.create(self.olena["id"], "beard", "oleg", datetime(2026, 10, 27, 14, 0), "admin")

    def last(self, uid: int = MASTER_ID) -> dict:
        return self.tg.last(uid)

    def kb(self, uid: int = MASTER_ID) -> list[tuple[str, str]]:
        return [(b["text"], b.get("callback_data", "")) for b in self.tg.buttons(self.last(uid))]

    async def admin(self, text: str) -> None:
        await self.send(msg(uid=ADMIN_ID, text=text))

    async def master(self, text: str) -> None:
        await self.send(msg(uid=MASTER_ID, text=text))

    async def press(self, data: str, uid: int = MASTER_ID) -> None:
        await self.send(cb(data, uid=uid))

    def alert(self) -> str:
        return self.tg.of("answerCallbackQuery")[-1].get("text", "")

    async def invite(self, master_id: str = "oleg") -> str:
        await self.press(f"aMi:{master_id}", uid=ADMIN_ID)
        m = re.search(r"https://t\.me/test_barber_bot\?start=(m[\w-]+)", self.last(ADMIN_ID)["text"])
        self.assertIsNotNone(m)
        return m.group(1)

    async def link(self, master_id: str = "oleg") -> None:
        await self.master(f"/start {await self.invite(master_id)}")


class LinkingTests(MasterTestCase):
    async def test_invite_join_and_unlink(self):
        await self.admin("/masters")
        text = self.last(ADMIN_ID)["text"]
        self.assertIn("⚪️ <b>Олег</b> — не підключено", text)
        self.assertIn(("🔗 Запросити: Олег", "aMi:oleg"), self.kb(ADMIN_ID))

        code = await self.invite()
        self.assertIn("одноразове, діє 48 год", self.last(ADMIN_ID)["text"])
        await self.master(f"/start {code}")
        welcome = self.last()
        self.assertIn("Вас підключено як майстра «Олег»", welcome["text"])
        keyboard = [b["text"] for row in welcome["reply_markup"]["keyboard"] for b in row]
        self.assertEqual(keyboard, ["📅 Мій день", "🗓 Мій тиждень", "🌴 Закрити час", "🔒 Мій закритий час"])
        self.assertIn("Майстер <b>Олег</b> підключився", self.last(ADMIN_ID)["text"])
        commands = [p for p in self.tg.of("setMyCommands") if p.get("scope", {}).get("chat_id") == MASTER_ID][-1]
        self.assertIn("my", [c["command"] for c in commands["commands"]])
        self.assertNotIn("stats", [c["command"] for c in commands["commands"]])
        self.assertEqual(self.app.master_links(self.tenant), {"oleg": MASTER_ID})

        # Посилання одноразове.
        await self.send(msg(uid=777, text=f"/start {code}"))
        self.assertIn("недійсне або вже використане", self.tg.last(777)["text"])

        await self.master("/start")
        self.assertIn("ви майстер у боті", self.last()["text"])

        await self.admin("/masters")
        self.assertIn("✅ <b>Олег</b> — ", self.last(ADMIN_ID)["text"])
        await self.press("aMu:oleg", uid=ADMIN_ID)
        self.assertIn("Відключити майстра <b>Олег</b>", self.last(ADMIN_ID)["text"])
        await self.press("aMuy:oleg", uid=ADMIN_ID)
        self.assertIn("відключено", self.last(ADMIN_ID)["text"])
        self.assertIn("Вас відключено", self.last()["text"])
        self.assertEqual(self.tg.of("deleteMyCommands")[-1]["scope"]["chat_id"], MASTER_ID)
        self.assertEqual(self.app.master_links(self.tenant), {})

    async def test_admin_unlinks_self_gets_client_menu(self):
        code = await self.invite()
        await self.admin(f"/start {code}")
        menus = [m["reply_markup"]["keyboard"] for m in self.tg.of("sendMessage")
                 if m["chat_id"] == ADMIN_ID and "keyboard" in m.get("reply_markup", {})]
        self.assertIn("📅 Мій день", [b["text"] for row in menus[-1] for b in row])

        await self.press("aMuy:oleg", uid=ADMIN_ID)
        last = self.last(ADMIN_ID)
        self.assertIn("Вас відключено", last["text"])
        keyboard = [b["text"] for row in last["reply_markup"]["keyboard"] for b in row]
        self.assertEqual(keyboard, ["📅 Записатися", "🗓 Мої записи", "💈 Послуги і ціни", "📍 Контакти"])
        self.assertEqual(self.app.master_links(self.tenant), {})

    async def test_expired_and_new_invite_replaces_old(self):
        old = await self.invite()
        new = await self.invite()
        await self.master(f"/start {old}")
        self.assertIn("недійсне", self.last()["text"])
        set_time(2026, 10, 28, 10, 0)  # минуло більше 48 год
        await self.master(f"/start {new}")
        self.assertIn("недійсне", self.last()["text"])
        self.assertEqual(self.app.master_links(self.tenant), {})

    async def test_one_person_one_master(self):
        await self.link("oleg")
        await self.link("andriy")
        self.assertEqual(self.app.master_links(self.tenant), {"andriy": MASTER_ID})

    async def test_no_access_without_link(self):
        await self.press("mD:20261027", uid=CLIENT_ID)
        self.assertEqual(self.alert(), "Немає доступу")
        await self.press("aMi:oleg", uid=CLIENT_ID)
        self.assertEqual(self.alert(), "Немає доступу")
        await self.send(msg(text="/my"))
        self.assertIn("Не знаю такої команди", self.tg.last(CLIENT_ID)["text"])


class MasterScreensTests(MasterTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.link()

    async def test_my_day_and_navigation(self):
        await self.master("📅 Мій день")  # пн — в Олега вихідний
        self.assertIn("Сьогодні, пн 26.10</b> · Олег — записів немає", self.last()["text"])
        self.assertIn("За графіком у вас вихідний", self.last()["text"])
        await self.press("mD:20261027")
        text = self.last()["text"]
        self.assertIn("Завтра, вт 27.10</b> · Олег — записів: 1", text)
        self.assertIn("Олена", text)
        self.assertNotIn("Іван", text)  # чужі записи не видно
        self.assertEqual(self.kb()[0], ("⚙️ 1 · 14:00 · Олена", f"mK:{self.b_oleg['id']}"))
        self.assertIn(("📅 Дата", "mDp"), self.kb())
        await self.master("/myweek")
        self.assertIn("Ваші записи на 7 днів", self.last()["text"])
        self.assertIn(("⚙️ 1 · вт 27.10 14:00 · Олена", f"mK:{self.b_oleg['id']}"), self.kb())

    async def test_card_and_no_show(self):
        await self.press(f"mK:{self.b_oleg['id']}")
        self.assertIn(f"Запис #{self.b_oleg['id']}", self.last()["text"])
        self.assertEqual(self.kb(), [("⬅️ До дня", "mD:20261027")])  # візит ще не сьогодні
        await self.press(f"mK:{self.b_andriy['id']}")  # чужий запис
        self.assertIn("неактуальна", self.alert())

        set_time(2026, 10, 27, 14, 20)
        await self.press(f"mK:{self.b_oleg['id']}")
        self.assertEqual(self.kb()[0], ("🚫 Не прийшов", f"mN:{self.b_oleg['id']}"))
        await self.press(f"mN:{self.b_oleg['id']}")
        self.assertEqual(self.db.get_booking(self.b_oleg["id"])["status"], "no_show")
        self.assertIn("не прийшов", self.alert())
        self.assertIn("Майстер Олег відмітив неявку", self.last(ADMIN_ID)["text"])
        await self.press(f"mN:{self.b_oleg['id']}")  # повторно — без другого сповіщення
        self.assertIn("неактуальна", self.alert())

    async def test_close_time_with_conflict(self):
        await self.master("🌴 Закрити час")
        self.assertIn(("Завтра", "mOd:20261027"), self.kb())
        await self.press("mOd:20261027")
        self.assertIn("ваш графік 10:00–19:00", self.last()["text"])
        self.assertIn(("🌴 Весь день", "mOe:20261027:w"), self.kb())
        self.assertIn(("18:30", "mOs:20261027:1830"), self.kb())
        await self.press("mOs:20261027:1300")
        ends = [d for _, d in self.kb()]
        self.assertEqual((ends[0], ends[-2]), ("mOe:20261027:1300:1330", "mOe:20261027:1300:1900"))
        await self.press("mOe:20261027:1300:1500")
        confirm = self.last()["text"]
        self.assertIn("Закрити <b>Завтра, вт 27.10 13:00–15:00</b>?", confirm)
        self.assertIn("14:00 · Борода · Олена", confirm)
        await self.press("mOy:20261027:1300:1500")
        self.assertIn("🔒 Закрито: <b>Завтра, вт 27.10 13:00–15:00</b>", self.last()["text"])
        admin = self.last(ADMIN_ID)
        self.assertIn("Майстер <b>Олег</b> закрив час: Завтра, вт 27.10 13:00–15:00", admin["text"])
        self.assertIn("домовтеся з клієнтами", admin["text"])
        self.assertEqual(self.tg.buttons(admin)[0]["callback_data"], f"aK:{self.b_oleg['id']}")
        self.assertNotIn("13:30", self.booking.free_slots("haircut", "oleg", date(2026, 10, 27)))
        self.assertIn("13:30", self.booking.free_slots("haircut", "andriy", date(2026, 10, 27)))

        await self.press("mOy:20261027:1300:1500")  # повторне натискання — без дубля
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM blocks"), 1)
        await self.master("📅 Мій день")
        await self.press("mD:20261027")
        self.assertIn("🔒 Закрито: 13:00–15:00", self.last()["text"])

    async def test_whole_day_and_reopen(self):
        await self.press("mOe:20261028:w")
        self.assertIn("Закрити <b>Ср, 28.10 (весь день)</b>?", self.last()["text"])
        await self.press("mOy:20261028:w")
        self.assertFalse(self.booking.free_slots("haircut", "oleg", date(2026, 10, 28)))
        await self.admin("/block oleg 29.10 12:00-13:00 лікар")  # закрив адмін — майстер не відкриє
        await self.master("🔒 Мій закритий час")
        text = self.last()["text"]
        self.assertIn("Натисніть, щоб відкрити назад", text)
        self.assertIn("Закрив адміністратор", text)
        self.assertIn("Чт 29.10 12:00–13:00", text)
        own = self.db.q("SELECT id FROM blocks WHERE created_by = 'master'")[0]["id"]
        admin_block = self.db.q("SELECT id FROM blocks WHERE created_by IS NULL")[0]["id"]
        self.assertEqual(self.kb(), [("🗑 Ср 28.10 (весь день)", f"mBd:{own}")])
        await self.press(f"mBd:{admin_block}")
        self.assertIn("неактуальна", self.alert())
        await self.press(f"mBd:{own}")
        self.assertEqual(self.alert(), "Час знову відкрито для запису")
        self.assertIn("Майстер <b>Олег</b> відкрив час: Ср, 28.10 (весь день)", self.last(ADMIN_ID)["text"])
        self.assertTrue(self.booking.free_slots("haircut", "oleg", date(2026, 10, 28)))

    async def test_past_day_rejected(self):
        await self.press("mOy:20261025:w")
        self.assertIn("неактуальна", self.alert())
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM blocks"), 0)


class MasterNotificationTests(MasterTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.link()
        self.tg.clear()

    async def test_new_cancel_by_client(self):
        await self.send(cb("bc:haircut:oleg:20261028:1200"))
        b = self.db.q("SELECT * FROM bookings ORDER BY id DESC")[0]
        new = self.last()
        self.assertIn("Новий запис до вас", new["text"])
        self.assertIn("Ср, 28.10 о 12:00", new["text"])
        self.assertIn("Іван · @ivan · +380501234567", new["text"])
        self.assertEqual(self.tg.buttons(new)[0]["callback_data"], f"mK:{b['id']}")
        await self.send(cb(f"cy:{b['id']}"))
        self.assertIn("Запис скасовано", self.last()["text"])

    async def test_other_master_not_notified(self):
        await self.send(cb("bc:haircut:andriy:20261028:1200"))
        self.assertEqual(self.tg.of("sendMessage", MASTER_ID), [])

    async def test_admin_cancel_and_reschedule(self):
        bid = self.b_oleg["id"]
        await self.press(f"aRy:{bid}:20261028:1000", uid=ADMIN_ID)
        text = self.last()["text"]
        self.assertIn("Запис перенесено", text)
        self.assertIn("Було: Завтра, вт 27.10, 14:00", text)
        self.assertIn("Стало: <b>Ср, 28.10, 10:00</b>", text)
        await self.press(f"acy:{bid}", uid=ADMIN_ID)
        self.assertIn("Запис скасовано", self.last()["text"])

    async def test_client_moves_to_other_master(self):
        set_time(2026, 10, 26, 9, 0)
        await self.send(cb(f"ry:{self.b_andriy['id']}:20261028:1200:oleg"))
        self.assertIn("Новий запис до вас", self.last()["text"])

    async def test_master_who_is_admin_gets_no_duplicates(self):
        self.db.kv_set(self.slug, "master_tg:oleg", str(ADMIN_ID))
        await self.send(cb("bc:haircut:oleg:20261028:1200"))
        texts = [t for t in self.tg.texts(ADMIN_ID)]
        self.assertEqual(len(texts), 1)
        self.assertIn("Новий запис", texts[0])

    async def test_morning_digest_once(self):
        sched = Scheduler(self.app)
        set_time(2026, 10, 27, 9, 5)
        await sched.master_digest(self.slug)
        text = self.last()["text"]
        self.assertIn("Доброго ранку, Олег!", text)
        self.assertIn("14:00", text)
        self.assertNotIn("Іван", text)
        await sched.master_digest(self.slug)
        self.assertEqual(len(self.tg.of("sendMessage", MASTER_ID)), 1)

    async def test_no_digest_on_day_off(self):
        set_time(2026, 10, 26, 9, 5)  # пн — в Олега вихідний, записів немає
        await Scheduler(self.app).master_digest(self.slug)
        self.assertEqual(self.tg.of("sendMessage", MASTER_ID), [])

    async def test_heads_up(self):
        sched = Scheduler(self.app)
        set_time(2026, 10, 27, 13, 40)
        await sched.master_heads_up(self.slug)
        self.assertEqual(self.tg.of("sendMessage", MASTER_ID), [])  # ще рано (за 20 хв)
        set_time(2026, 10, 27, 13, 46)
        await sched.master_heads_up(self.slug)
        self.assertIn("<b>О 14:00</b> (через 14 хв) — Олена", self.last()["text"])
        await sched.master_heads_up(self.slug)
        self.assertEqual(len(self.tg.of("sendMessage", MASTER_ID)), 1)


class MasterAITests(MasterTestCase):
    async def test_master_gets_work_only_ai_without_tools(self):
        await self.link()
        self.llm.add(text_reply("Завтра о 14:00 — Олена, борода."))
        await self.master("Хто в мене завтра?")
        payload = self.llm.payloads[-1]
        self.assertNotIn("tools", payload)
        system = payload["system"][0]["text"] + payload["system"][1]["text"]
        self.assertIn("робочий помічник майстрів", system)
        self.assertIn("Я допомагаю лише з роботою", system)
        self.assertIn("Імʼя: Олег", system)
        self.assertIn("14:00–14:30 · Борода · Олена", system)
        self.assertNotIn("Іван", payload["system"][1]["text"])  # чужі записи не потрапляють у промпт
        self.assertEqual(self.last()["text"], "Завтра о 14:00 — Олена, борода.")

    async def test_client_prompt_is_topic_locked(self):
        self.llm.add(text_reply("Я допомагаю лише із записом і питаннями про наш заклад."))
        await self.send(msg(text="Напиши твір про осінь"))
        payload = self.llm.payloads[-1]
        self.assertIn("tools", payload)
        self.assertIn("Тема розмови — найважливіше правило", payload["system"][0]["text"])
        self.assertNotIn("робочий помічник", payload["system"][0]["text"])


if __name__ == "__main__":
    unittest.main()
