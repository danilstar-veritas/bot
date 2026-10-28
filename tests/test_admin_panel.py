"""Панель адміністратора: день із навігацією й фільтром, картка запису, перенесення, пошук клієнтів,
виручка, вечірній підсумок, вивантаження в Excel."""

from __future__ import annotations

import io
import unittest
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

from barberbot.app import BotApp
from barberbot.scheduler import Scheduler
from barberbot.xlsx import build_xlsx, column_name

from .helpers import ADMIN_ID, CLIENT_ID, cb, make_tenant, msg, set_time
from .test_app import BotTestCase


class AdminPanelTests(BotTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ivan = self.make_client()
        self.olena = self.db.create_offline_client(self.slug, "Олена", "+380671234567", self.tenant.now())
        self.b1 = self.booking.create(self.ivan["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        self.b2 = self.booking.create(self.olena["id"], "beard", "oleg", datetime(2026, 10, 27, 14, 0), "admin")

    def last(self) -> dict:
        return self.tg.last(ADMIN_ID)

    def kb(self) -> list[tuple[str, str]]:
        return [(b["text"], b["callback_data"]) for b in self.tg.buttons(self.last())]

    async def admin(self, text: str) -> None:
        await self.send(msg(uid=ADMIN_ID, text=text))

    async def press(self, data: str) -> None:
        await self.send(cb(data, uid=ADMIN_ID))

    # ---------------------------------------------------------------- день
    async def test_day_navigation_and_master_filter(self):
        await self.admin("/today")  # пн 26.10 — записів немає
        self.assertIn("Сьогодні, пн 26.10</b> — записів немає", self.last()["text"])
        self.assertIn(("Завтра ▶️", "aD:20261027:*"), self.kb())
        self.assertIn(("📅 Дата", "aDp:*"), self.kb())

        await self.press("aD:20261027:*")
        self.assertEqual(self.tg.calls[-2][0], "editMessageText")  # гортання — у тому самому повідомленні
        text = self.last()["text"]
        self.assertIn("<b>1. 12:00–13:00</b>", text)
        self.assertIn("<b>2. 14:00–14:30</b>", text)
        self.assertEqual(self.kb()[:2], [("⚙️ 1 · 12:00 · Іван", f"aK:{self.b1['id']}"),
                                         ("⚙️ 2 · 14:00 · Олена", f"aK:{self.b2['id']}")])
        self.assertIn(("◀️ Сьогодні", "aD:20261026:*"), self.kb())
        self.assertIn(("✅ 👥 Усі", "aD:20261027:*"), self.kb())

        await self.press("aD:20261027:oleg")
        text = self.last()["text"]
        self.assertIn("Завтра, вт 27.10</b> · Олег — записів: 1", text)
        self.assertNotIn("Іван", text)
        self.assertIn(("✅ Олег", "aD:20261027:oleg"), self.kb())
        self.assertIn(("Андрій", "aD:20261027:andriy"), self.kb())

        await self.press("aDp:oleg")
        days = [d for _, d in self.kb()]
        self.assertIn("aD:20261019:oleg", days)  # тиждень назад
        self.assertIn("aD:20261108:oleg", days)  # на 14 днів уперед

    async def test_day_command(self):
        await self.admin("/day 27.10")
        self.assertIn("Завтра, вт 27.10</b> — записів: 2", self.last()["text"])
        await self.admin("/day абв")
        self.assertIn("/day 30.10", self.last()["text"])

    # ---------------------------------------------------------------- картка запису
    async def test_booking_card(self):
        await self.press(f"aK:{self.b1['id']}")
        text = self.last()["text"]
        self.assertIn(f"📋 <b>Запис #{self.b1['id']}</b>", text)
        self.assertIn("📱 Записався сам", text)
        self.assertEqual(self.kb(), [("🔁 Перенести", f"aRs:{self.b1['id']}"), ("🗑 Скасувати", f"acx:{self.b1['id']}"),
                                     ("👤 Змінити майстра", f"aRm:{self.b1['id']}"),
                                     ("👤 Клієнт", f"aC:{self.ivan['id']}"), ("✉️ Написати", f"ar:{self.ivan['id']}")])
        # Клієнт без Telegram — без «Написати»; видно, хто записав.
        await self.press(f"aK:{self.b2['id']}")
        self.assertIn("📞 Записав адміністратор", self.last()["text"])
        self.assertNotIn("✉️ Написати", [t for t, _ in self.kb()])

    async def test_no_show_after_visit_started(self):
        set_time(2026, 10, 27, 12, 30)  # візит уже почався — раніше відмітити неявку було неможливо
        await self.press(f"aK:{self.b1['id']}")
        self.assertEqual(self.kb()[0], ("🚫 Не прийшов", f"ans:{self.b1['id']}"))
        self.assertNotIn(f"aRs:{self.b1['id']}", [d for _, d in self.kb()])
        await self.press(f"ans:{self.b1['id']}")
        self.assertEqual(self.db.get_booking(self.b1["id"])["status"], "no_show")
        self.assertIn("🚫 Клієнт не прийшов", self.last()["text"])
        self.assertIn("не прийшов", self.tg.of("answerCallbackQuery")[-1]["text"])

    # ---------------------------------------------------------------- перенесення
    async def test_admin_reschedule_notifies_client(self):
        bid = self.b1["id"]
        await self.press(f"aRs:{bid}")
        self.assertIn(f"Перенесення запису #{bid}", self.last()["text"])
        self.assertIn(f"aRd:{bid}:20261028", [d for _, d in self.kb()])
        await self.press(f"aRd:{bid}:20261028")
        self.assertIn(f"aRt:{bid}:20261028:1000", [d for _, d in self.kb()])
        await self.press(f"aRt:{bid}:20261028:1000")
        confirm = self.last()["text"]
        self.assertIn("Перенести запис?", confirm)
        self.assertIn("Стане: <b>Ср, 28.10, 10:00 · Андрій</b>", confirm)
        self.assertIn("Клієнт отримає повідомлення", confirm)
        await self.press(f"aRy:{bid}:20261028:1000")
        self.assertEqual(self.db.get_booking(bid)["start_at"], "2026-10-28 10:00")
        self.assertIn("🔁 <b>Перенесено</b>", self.last()["text"])
        self.assertIn("Адміністратор переніс ваш запис", self.tg.last(CLIENT_ID)["text"])
        self.assertIn("Стало: <b>Ср, 28.10, 10:00</b>", self.tg.last(CLIENT_ID)["text"])

    async def test_admin_reschedule_ignores_client_lead_time(self):
        set_time(2026, 10, 27, 9, 45)  # клієнт міг би лише з 10:45, адмін — і на 10:00
        await self.press(f"aRd:{self.b1['id']}:20261027")
        self.assertIn(f"aRt:{self.b1['id']}:20261027:1000", [d for _, d in self.kb()])

    # ---------------------------------------------------------------- зміна майстра
    async def test_change_master_same_time(self):
        bid = self.b1["id"]  # стрижка в Андрія, вт 27.10 12:00; Олег о 12:00 вільний
        self.db.kv_set(self.slug, "master_tg:andriy", "701")
        self.db.kv_set(self.slug, "master_tg:oleg", "702")
        await self.press(f"aRm:{bid}")
        self.assertIn(f"Інший майстер для запису #{bid}", self.last()["text"])
        self.assertEqual(self.kb(), [("💈 Олег", f"aRM:{bid}:oleg"), ("⬅️ Назад", f"aKe:{bid}")])

        await self.press(f"aRM:{bid}:oleg")  # той самий час вільний — одразу підтвердження
        confirm = self.last()["text"]
        self.assertIn("Було: Завтра, вт 27.10, 12:00 · Андрій", confirm)
        self.assertIn("Стане: <b>Завтра, вт 27.10, 12:00 · Олег</b>", confirm)
        self.assertEqual(self.kb()[0], ("✅ Перенести", f"aRy:{bid}:20261027:1200:oleg"))
        self.assertEqual(self.kb()[1], ("⬅️ Інший час", f"aRd:{bid}:20261027:oleg"))

        await self.press(f"aRy:{bid}:20261027:1200:oleg")
        b = self.db.get_booking(bid)
        self.assertEqual((b["master_id"], b["master_name"], b["start_at"]), ("oleg", "Олег", "2026-10-27 12:00"))
        self.assertIn("🔁 <b>Перенесено</b>", self.last()["text"])
        client_text = self.tg.last(CLIENT_ID)["text"]
        self.assertIn("Було: Завтра, вт 27.10, 12:00 · Андрій", client_text)
        self.assertIn("Стало: <b>Завтра, вт 27.10, 12:00 · Олег</b>", client_text)
        self.assertIn("Запис перейшов до іншого майстра", self.tg.last(701)["text"])
        self.assertIn("Новий запис до вас", self.tg.last(702)["text"])

    async def test_change_master_busy_picks_other_day(self):
        bid = self.b1["id"]
        self.booking.create(self.olena["id"], "haircut", "oleg", datetime(2026, 10, 27, 12, 0), "admin")
        await self.press(f"aRM:{bid}:oleg")
        self.assertIn("О 12:00 цей майстер зайнятий", self.last()["text"])
        days = [d for _, d in self.kb()]
        self.assertIn(f"aRd:{bid}:20261028:oleg", days)
        self.assertNotIn(f"aRd:{bid}:20261102:oleg", days)  # понеділок у Олега вихідний
        self.assertEqual(self.kb()[-1], ("⬅️ Назад", f"aRm:{bid}"))

        await self.press(f"aRd:{bid}:20261028:oleg")
        self.assertIn("Олег", self.last()["text"])
        self.assertIn(f"aRt:{bid}:20261028:1000:oleg", [d for _, d in self.kb()])
        self.assertEqual(self.kb()[-1], ("⬅️ Назад", f"aRs:{bid}:oleg"))
        await self.press(f"aRt:{bid}:20261028:1000:oleg")
        self.assertIn("Стане: <b>Ср, 28.10, 10:00 · Олег</b>", self.last()["text"])
        await self.press(f"aRy:{bid}:20261028:1000:oleg")
        b = self.db.get_booking(bid)
        self.assertEqual((b["master_id"], b["start_at"]), ("oleg", "2026-10-28 10:00"))

    async def test_change_master_only_to_masters_with_service(self):
        combo = self.booking.create(self.ivan["id"], "combo", "andriy", datetime(2026, 10, 28, 12, 0), "buttons")
        await self.press(f"aK:{combo['id']}")
        self.assertNotIn(f"aRm:{combo['id']}", [d for _, d in self.kb()])  # комбо робить лише Андрій
        await self.press(f"aRM:{combo['id']}:oleg")
        self.assertIn("неактуальна", self.tg.of("answerCallbackQuery")[-1]["text"])
        self.assertEqual(self.db.get_booking(combo["id"])["master_id"], "andriy")

    # ---------------------------------------------------------------- клієнти
    async def test_find_and_client_card(self):
        await self.admin("/find іва")
        card = self.last()["text"]
        self.assertIn("👤 <b>Іван</b>", card)
        self.assertIn("@ivan · +380501234567", card)
        self.assertIn("Візитів: 0", card)
        self.assertIn("Майбутні записи:", card)
        self.assertIn((f"⚙️ 27.10 12:00 · Чоловіча стрижка", f"aK:{self.b1['id']}"), self.kb())
        self.assertIn(("📞 Записати", f"aCb:{self.ivan['id']}"), self.kb())

        await self.admin("/find 0671")
        self.assertIn("👤 <b>Олена</b>", self.last()["text"])
        self.assertIn("📵 Немає в Telegram", self.last()["text"])
        self.assertNotIn("✉️ Написати", [t for t, _ in self.kb()])

        await self.admin("/find Зюзя")
        self.assertIn("нікого не знайдено", self.last()["text"])
        await self.admin("/find")
        self.assertIn("/find Іван", self.last()["text"])

        self.db.create_offline_client(self.slug, "Іванна", "0509998877", self.tenant.now())
        await self.admin("/find Іван")
        self.assertIn("Знайдено: 2", self.last()["text"])

    async def test_client_history(self):
        set_time(2026, 10, 27, 20, 0)
        await self.press(f"aC:{self.olena['id']}")
        card = self.last()["text"]
        self.assertIn("Візитів: 1", card)
        self.assertIn("Разом: 300 грн", card)
        self.assertIn("Останній візит: Сьогодні, вт 27.10 · Борода", card)

    async def test_book_from_client_card_uses_same_client(self):
        await self.press(f"aCb:{self.olena['id']}")
        await self.press("aBt:haircut:andriy:20261028:1200")
        card = self.last()["text"]
        self.assertIn("Олена", card)
        self.assertIn("уже є в базі", card)
        await self.press("aBy")
        b = self.db.q("SELECT * FROM bookings ORDER BY id DESC")[0]
        self.assertEqual((b["client_id"], b["start_at"]), (self.olena["id"], "2026-10-28 12:00"))
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM clients WHERE tg_id < 0"), 1)  # без дубля

    # ---------------------------------------------------------------- гроші
    async def test_stats_revenue(self):
        set_time(2026, 10, 27, 20, 0)
        await self.admin("/stats")
        text = self.last()["text"]
        self.assertIn("<b>Виручка</b>", text)
        self.assertIn("800 грн · середній чек 400 грн", text)
        self.assertIn("Андрій: 1 · 500 грн", text)
        self.assertIn("Олег: 1 · 300 грн", text)
        await self.admin("/stats 7")
        self.assertIn("Статистика за 7 днів", self.last()["text"])

    async def test_evening_report_once(self):
        sched = Scheduler(self.app)
        set_time(2026, 10, 27, 21, 5)
        await sched.evening_report(self.slug)
        text = self.last()["text"]
        self.assertIn("Підсумок дня · Сьогодні, вт 27.10", text)
        self.assertIn("Виручка: <b>800 грн</b>", text)
        self.assertIn("Завтра записів: 0", text)
        sent = len(self.tg.of("sendMessage", ADMIN_ID))
        await sched.evening_report(self.slug)
        self.assertEqual(len(self.tg.of("sendMessage", ADMIN_ID)), sent)

    # ---------------------------------------------------------------- Excel
    async def test_export_excel(self):
        await self.admin("/export")
        doc = self.tg.of("sendDocument")[-1]
        self.assertEqual(doc["chat_id"], ADMIN_ID)
        self.assertTrue(doc["filename"].endswith(".xlsx"))
        self.assertIn("Записи з 26.09.2026 (і всі майбутні): 2", doc["caption"])
        with zipfile.ZipFile(io.BytesIO(doc["content"])) as z:
            sheet = z.read("xl/worksheets/sheet1.xml").decode()
        ET.fromstring(sheet)  # коректний XML
        for value in ("Олена", "+380671234567", "Чоловіча стрижка", "<v>500</v>", "заплановано", "адмін"):
            self.assertIn(value, sheet)
        await self.admin("/export abc")
        self.assertIn("/export 90", self.last()["text"])


class PriceTests(BotTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        # Додаток «Миття» до стрижки — щоб перевірити перерахунок комбінації.
        self.tenant = make_tenant(extra='\n[[services]]\nid = "wash"\ntitle = "Миття"\nduration = 15\nprice = 150\n'
                                        'addon_for = ["haircut"]\n')
        self.slug = self.tenant.slug
        self.app = BotApp(self.settings, [self.tenant], self.db, None, api_factory=lambda t: self.tg)
        self.booking = self.app.bookings[self.slug]

    def kb(self) -> list[tuple[str, str]]:
        return [(b["text"], b["callback_data"]) for b in self.tg.buttons(self.tg.last(ADMIN_ID))]

    async def test_change_and_restore_price(self):
        await self.send(msg(uid=ADMIN_ID, text="/prices"))
        self.assertIn(("Чоловіча стрижка — 500 грн", "aPe:haircut"), self.kb())
        self.assertIn(("Миття — 150 грн", "aPe:wash"), self.kb())
        self.assertNotIn("aPe:haircut+wash", [d for _, d in self.kb()])  # комбінації — автоматично

        await self.send(cb("aPe:haircut", uid=ADMIN_ID))
        self.assertIn("Зараз: <b>500 грн</b>", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="дорого"))
        self.assertIn("Не схоже на ціну", self.tg.last(ADMIN_ID)["text"])
        await self.send(msg(uid=ADMIN_ID, text="700 грн"))
        text = self.tg.last(ADMIN_ID)["text"]
        self.assertIn("<b>Чоловіча стрижка</b>: 500 грн → <b>700 грн</b>", text)
        self.assertIn("комбінацій із додатками перераховано", text)
        self.assertIn(("✏️ Чоловіча стрижка — 700 грн", "aPe:haircut"), self.kb())
        self.assertEqual(self.tenant.services["haircut+wash"].price, 850)

        # Клієнт бачить нову ціну, новий запис — за новою ціною.
        await self.send(msg(text="💈 Послуги і ціни"))
        self.assertIn("700 грн", self.tg.last(CLIENT_ID)["text"])
        client = self.make_client()
        b = self.booking.create(client["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        self.assertEqual(b["price"], 700)

        # Після перезапуску бота й /reload ціна лишається.
        app2 = BotApp(self.settings, [make_tenant()], self.db, None, api_factory=lambda t: self.tg)
        self.assertEqual(app2.tenants[self.slug].services["haircut"].price, 700)
        await self.send(msg(uid=ADMIN_ID, text="/reload"))
        self.assertEqual(self.app.tenants[self.slug].services["haircut"].price, 700)

        await self.send(cb("aPe:haircut", uid=ADMIN_ID))
        self.assertIn("У файлі налаштувань: 500 грн", self.tg.last(ADMIN_ID)["text"])
        await self.send(cb("aPr:haircut", uid=ADMIN_ID))
        self.assertEqual(self.app.tenants[self.slug].services["haircut"].price, 500)
        self.assertIsNone(self.db.kv_get(self.slug, "price:haircut"))
        self.assertIn(("Чоловіча стрижка — 500 грн", "aPe:haircut"), self.kb())

    async def test_state_does_not_swallow_menu_and_clients_cannot(self):
        await self.send(cb("aPe:haircut", uid=ADMIN_ID))
        await self.send(msg(uid=ADMIN_ID, text="📍 Контакти"))
        self.assertIn("вул. Тестова", self.tg.last(ADMIN_ID)["text"])
        self.assertIsNone(self.app.states.get((self.slug, ADMIN_ID)))
        await self.send(cb("aPe:haircut"))
        self.assertEqual(self.tg.of("answerCallbackQuery")[-1]["text"], "Немає доступу")
        await self.send(msg(text="/prices"))
        self.assertIn("Не знаю такої команди", self.tg.last(CLIENT_ID)["text"])


class XlsxTests(unittest.TestCase):
    def test_build(self):
        data = build_xlsx(["Ім'я", "Ціна"], [["x<&>\x01", 5], [None, 2.5]], sheet="Аркуш", widths=[10, 8])
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            self.assertTrue({"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml",
                             "xl/styles.xml"} <= names)
            for name in names:
                ET.fromstring(z.read(name))  # усі частини — коректний XML
            sheet = z.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("x&lt;&amp;&gt;", sheet)
        self.assertIn("<v>2.5</v>", sheet)
        self.assertEqual((column_name(0), column_name(25), column_name(26), column_name(27)), ("A", "Z", "AA", "AB"))


if __name__ == "__main__":
    unittest.main()
