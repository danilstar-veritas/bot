"""Налаштування, розрахунок вільного часу і правила записів."""

from __future__ import annotations

import re
import string
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from barberbot import clock
from barberbot.booking import BookingError, BookingService
from barberbot.config import ConfigError, load_settings, load_tenant, parse_day_spec, parse_user_date
from barberbot.db import DB
from barberbot.slots import free_starts
from barberbot.texts import TEXTS
from barberbot.util import is_affirmative, normalize_phone

from .helpers import TENANT_TOML, TOKEN, make_tenant, set_time

ROOT = Path(__file__).resolve().parent.parent


def write_toml(text: str, name: str = "x.toml") -> Path:
    path = Path(tempfile.mkdtemp()) / name
    path.write_text(text, encoding="utf-8")
    return path


class ConfigTests(unittest.TestCase):
    def tearDown(self):
        clock.set_fixed(None)

    def test_demo_config_loads(self):
        text = (ROOT / "config/tenants/demo-barbershop.toml").read_text(encoding="utf-8")
        text = text.replace("ВСТАВТЕ_ТОКЕН_ВІД_BOTFATHER", TOKEN).replace("admins = []", "admins = [42]")
        # Без картки передоплата вимкнена і check про це попереджає.
        no_card = load_tenant(write_toml(text, "demo.toml"))
        self.assertFalse(no_card.prepay_enabled)
        self.assertEqual(len(no_card.warnings), 1)
        self.assertIn("[prepayment]", no_card.warnings[0])
        t = load_tenant(write_toml(text.replace('card = ""', 'card = "5375 0000 0000 0000"'), "demo.toml"))
        self.assertTrue(t.prepay_enabled)
        self.assertEqual((t.prepay_amount, t.prepay_hours), (150, 2))
        self.assertEqual((t.max_per_week, t.max_active_per_client), (5, 0))
        self.assertEqual(len(t.visible_services()), 16)
        # Розділи списку послуг — у порядку з налаштувань; діти — окремо хлопчики і дівчатка.
        self.assertEqual([(g, [s.id for s in ss]) for g, ss in t.service_groups()], [
            ("👨 Чоловічі", ["haircut", "beard", "combo", "buzz"]),
            ("👩 Жіночі", ["women_short", "women_medium", "women_long", "pixie", "trim_ends", "bangs"]),
            ("👦 Хлопчики (до 8 років)", ["kids_boy", "kids_buzz"]),
            ("👧 Дівчатка (до 8 років)", ["kids_girl", "kids_girl_long", "kids_ends", "kids_bangs"]),
        ])
        self.assertNotIn("kids", t.services)
        # Хлопчиків стрижуть усі майстри (без бороди), дівчаток — лише майстрині.
        for sid in ("kids_boy", "kids_buzz"):
            self.assertEqual({m.id for m in t.masters_for(sid)}, {"andriy", "oleg", "olena", "maryna"})
        for sid in ("kids_girl", "kids_girl_long", "kids_ends", "kids_bangs"):
            self.assertEqual({m.id for m in t.masters_for(sid)}, {"olena", "maryna"})
        # Миття голови — лише додатком, до всього, крім кінчиків і бороди; у всіх майстрів.
        combos = {s.id: s for s in t.services.values() if s.base_id}
        self.assertTrue(t.services["wash"].hidden)
        self.assertTrue(all(c.endswith("+wash") for c in combos))
        self.assertEqual({c.split("+")[0] for c in combos},
                         {"haircut", "combo", "buzz", "women_short", "women_medium", "women_long", "pixie", "bangs",
                          "kids_boy", "kids_buzz", "kids_girl", "kids_girl_long", "kids_bangs"})
        self.assertEqual({m.id for m in t.masters_for("haircut+wash")}, {"andriy", "oleg", "olena", "maryna"})
        self.assertEqual((combos["women_long+wash"].duration, combos["women_long+wash"].price), (105, 1100))
        self.assertEqual([s.id for s in t.addons_for("haircut", "oleg")], ["haircut+wash"])
        self.assertEqual(list(t.masters), ["andriy", "oleg", "olena", "maryna"])
        # Жіночі стрижки — лише майстрині; вони ж роблять дитячу і просту чоловічу (без бороди).
        for m in ("andriy", "oleg"):
            self.assertNotIn("women_long", t.masters[m].services)
        for m in ("olena", "maryna"):
            self.assertIn("women_long", t.masters[m].services)
            self.assertIn("kids_girl", t.masters[m].services)
            self.assertIn("haircut", t.masters[m].services)
            self.assertIn("buzz", t.masters[m].services)
            self.assertNotIn("beard", t.masters[m].services)
            self.assertNotIn("combo", t.masters[m].services)
        self.assertEqual(t.masters["oleg"].schedule[0], [])  # пн — вихідний
        self.assertEqual(len(t.masters["oleg"].schedule[6]), 1)  # нд — 11-17
        self.assertTrue({"kids_boy", "kids_buzz"} <= set(t.masters["oleg"].services))
        self.assertNotIn("kids_girl", t.masters["oleg"].services)
        self.assertEqual({m.id for m in t.masters_for("kids_girl+wash")}, {"olena", "maryna"})
        self.assertEqual(t.price_str(850), "850 грн")
        self.assertEqual(t.warnings, [])
        summary = t.schedule_summary("uk")
        self.assertIn("Пн–пт: 10:00–20:00", summary)
        self.assertIn("Нд: 11:00–17:00", summary)

    def test_demo_without_token_explains(self):
        with self.assertRaises(ConfigError) as cm:
            load_tenant(ROOT / "config/tenants/demo-barbershop.toml")
        self.assertIn("BotFather", str(cm.exception))

    def test_demo_loads_for_console_without_token(self):
        t = load_tenant(ROOT / "config/tenants/demo-barbershop.toml", require_token=False)
        self.assertEqual(t.bot_token, "")
        self.assertEqual(t.name, "Студія «Гострий стиль»")

    def test_settings_file_loads(self):
        s = load_settings(ROOT / "config/settings.toml", ROOT)
        self.assertEqual(s.model, "claude-haiku-5-5")
        self.assertEqual(s.effort, "low")
        self.assertEqual(s.data_dir, ROOT / "data")

    def test_bad_schedule(self):
        bad = TENANT_TOML.format(token=TOKEN, admin=1, require_phone="true").replace(
            'tue = "10:00-19:00"', 'tue = "з 10 до 19"')
        with self.assertRaises(ConfigError) as cm:
            load_tenant(write_toml(bad))
        self.assertIn("tue", str(cm.exception))

    def test_unknown_service_in_master(self):
        bad = TENANT_TOML.format(token=TOKEN, admin=1, require_phone="true").replace(
            'services = ["haircut", "beard"]', 'services = ["haircut", "massage"]')
        with self.assertRaises(ConfigError) as cm:
            load_tenant(write_toml(bad))
        self.assertIn("massage", str(cm.exception))

    def test_smart_quotes_hint(self):
        bad = TENANT_TOML.format(token=TOKEN, admin=1, require_phone="true").replace(
            'name = "Тест Барбер"', 'name = “Тест Барбер”')
        with self.assertRaises(ConfigError) as cm:
            load_tenant(write_toml(bad))
        self.assertIn("лапки", str(cm.exception))

    def test_parse_helpers(self):
        self.assertEqual(len(parse_day_spec("10:00-14:00, 15:00-19:00", "x")), 2)
        self.assertEqual(parse_day_spec("off", "x"), [])
        today = date(2026, 10, 26)
        self.assertEqual(parse_user_date("30.10", today), date(2026, 10, 30))
        self.assertEqual(parse_user_date("05.01", today), date(2027, 1, 5))
        self.assertEqual(parse_user_date("завтра", today), date(2026, 10, 27))
        self.assertEqual(parse_user_date("2026-11-02", today), date(2026, 11, 2))
        self.assertIsNone(parse_user_date("31.02", today))

    def test_texts_complete_in_all_languages(self):
        fmt = string.Formatter()

        def fields(s: str) -> set[str]:
            return {f for _, f, _, _ in fmt.parse(s) if f}

        base = TEXTS["uk"]
        for lang, texts in TEXTS.items():
            self.assertEqual(set(texts), set(base), f"{lang}: різний набір ключів")
            for key, value in texts.items():
                self.assertEqual(fields(value), fields(base[key]), f"{lang}.{key}: різні плейсхолдери")

    def test_phone_and_affirmative(self):
        self.assertEqual(normalize_phone("+380 (50) 123-45-67"), "+380501234567")
        self.assertEqual(normalize_phone("0501234567"), "0501234567")
        self.assertEqual(normalize_phone("380501234567", from_contact=True), "+380501234567")
        self.assertIsNone(normalize_phone("мій номер 0501234567"))
        self.assertIsNone(normalize_phone("12345"))
        for yes in ("так", "Так!", "ок", "так, дякую", "yes please", "+", "Да, верно"):
            self.assertTrue(is_affirmative(yes), yes)
        for no in ("так, але о 18", "так, о 18:00", "ні", "а можна завтра?", "так так так так так"):
            self.assertFalse(is_affirmative(no), no)


class SlotTests(unittest.TestCase):
    def setUp(self):
        set_time(2026, 10, 26, 9, 0)  # понеділок
        self.tenant = make_tenant()
        self.db = DB(":memory:")
        self.svc = BookingService(self.tenant, self.db)
        self.client = self.db.upsert_client(self.tenant.slug, 1, "Іван", None, None, "uk", self.tenant.now())["id"]
        self.client2 = self.db.upsert_client(self.tenant.slug, 2, "Петро", None, None, "uk", self.tenant.now())["id"]

    def tearDown(self):
        clock.set_fixed(None)
        self.db.close()

    def test_free_starts_basic(self):
        d = datetime(2026, 1, 1)
        work = [(d.replace(hour=10), d.replace(hour=12))]
        busy = [(d.replace(hour=10, minute=30), d.replace(hour=11))]
        starts = free_starts(work, busy, 30, 30, d.replace(hour=9))
        self.assertEqual([s.strftime("%H:%M") for s in starts], ["10:00", "11:00", "11:30"])

    def test_monday_only_andriy(self):
        slots = self.svc.free_slots("haircut", "any", date(2026, 10, 26))
        self.assertEqual(list(slots)[0], "10:00")
        self.assertEqual(list(slots)[-1], "18:00")
        self.assertEqual(len(slots), 17)
        self.assertTrue(all(m == ["andriy"] for m in slots.values()))
        self.assertEqual(self.svc.free_slots("haircut", "oleg", date(2026, 10, 26)), {})

    def test_tuesday_both_masters(self):
        slots = self.svc.free_slots("haircut", "any", date(2026, 10, 27))
        self.assertEqual(slots["10:00"], ["andriy", "oleg"])
        # Олег не робить комбо
        self.assertEqual(self.svc.free_slots("combo", "any", date(2026, 10, 27))["10:00"], ["andriy"])

    def test_sunday_and_horizon(self):
        self.assertEqual(self.svc.free_slots("haircut", "any", date(2026, 11, 1)), {})
        self.assertEqual(self.svc.free_slots("haircut", "any", date(2026, 11, 20)), {})
        days = self.svc.available_days("haircut", "any")
        self.assertNotIn(date(2026, 11, 1), days)
        self.assertEqual(days[0], date(2026, 10, 26))

    def test_lead_time(self):
        set_time(2026, 10, 26, 12, 10)
        slots = self.svc.free_slots("haircut", "andriy", date(2026, 10, 26))
        self.assertEqual(list(slots)[0], "13:30")

    def test_booking_blocks_slot(self):
        start = datetime(2026, 10, 26, 10, 0)
        b = self.svc.create(self.client, "haircut", "andriy", start, "buttons")
        self.assertEqual(b["end_at"], "2026-10-26 11:00")
        slots = self.svc.free_slots("haircut", "andriy", date(2026, 10, 26))
        self.assertNotIn("10:00", slots)
        self.assertNotIn("10:30", slots)
        self.assertIn("11:00", slots)
        with self.assertRaises(BookingError) as cm:
            self.svc.create(self.client2, "beard", "andriy", datetime(2026, 10, 26, 10, 30), "buttons")
        self.assertEqual(cm.exception.code, "slot_taken")

    def test_buffer(self):
        self.tenant.buffer_min = 15
        self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, 26, 10, 0), "buttons")
        slots = self.svc.free_slots("haircut", "andriy", date(2026, 10, 26))
        self.assertNotIn("11:00", slots)
        self.assertIn("11:30", slots)

    def test_blocks_and_holidays(self):
        day = date(2026, 10, 27)
        start = datetime.combine(day, datetime.min.time())
        _, conflicts = self.svc.add_block("andriy", start, start + timedelta(days=1), "відпустка")
        self.assertEqual(conflicts, [])
        slots = self.svc.free_slots("haircut", "any", day)
        self.assertTrue(all(m == ["oleg"] for m in slots.values()))
        self.tenant.holidays.add(day)
        self.assertEqual(self.svc.free_slots("haircut", "any", day), {})

    def test_limits_and_duplicates(self):
        self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, 27, 10, 0), "buttons")
        with self.assertRaises(BookingError) as cm:
            self.svc.create(self.client, "beard", "oleg", datetime(2026, 10, 27, 10, 30), "buttons")
        self.assertEqual(cm.exception.code, "duplicate")
        self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, 28, 10, 0), "buttons")
        with self.assertRaises(BookingError) as cm:
            self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, 29, 10, 0), "buttons")
        self.assertEqual(cm.exception.code, "too_many")

    def test_week_limit_per_client(self):
        # 5 записів на календарний тиждень (пн–нд) за датою візиту; ліміт «2 майбутні» вимкнено.
        self.tenant.max_active_per_client = 0
        self.tenant.max_per_week = 5
        for day in (27, 28, 29, 30, 31):  # вт–сб
            self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, day, 10, 0), "buttons")
        with self.assertRaises(BookingError) as cm:
            self.svc.create(self.client, "beard", "andriy", datetime(2026, 10, 27, 14, 0), "buttons")
        self.assertEqual((cm.exception.code, cm.exception.info["limit"]), ("week_limit", 5))
        # Наступний тиждень — вже можна; інший клієнт — теж; адмін — без обмеження.
        nxt = self.svc.create(self.client, "haircut", "andriy", datetime(2026, 11, 2, 10, 0), "buttons")
        self.svc.create(self.client2, "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "buttons")
        by_admin = self.svc.create(self.client, "beard", "oleg", datetime(2026, 10, 27, 14, 0), "admin")
        # Перенести запис з наступного тижня на цей не можна. Запис адміна теж займає місце в тижні,
        # а скасовані не рахуються.
        with self.assertRaises(BookingError) as cm:
            self.svc.reschedule(nxt["id"], datetime(2026, 10, 30, 15, 0), None, self.client)
        self.assertEqual(cm.exception.code, "week_limit")
        first = self.db.q("SELECT id FROM bookings WHERE client_id = ? ORDER BY start_at", self.client)[0]["id"]
        self.svc.cancel(first, "client", self.client)
        with self.assertRaises(BookingError):  # 4 своїх + 1 від адміна = 5
            self.svc.reschedule(nxt["id"], datetime(2026, 10, 30, 15, 0), None, self.client)
        self.svc.cancel(by_admin["id"], "admin")
        self.svc.reschedule(nxt["id"], datetime(2026, 10, 30, 15, 0), None, self.client)

    def test_window_errors(self):
        for start, code in [(datetime(2026, 10, 26, 8, 0), "past"), (datetime(2026, 10, 26, 9, 30), "too_soon"),
                            (datetime(2026, 11, 20, 10, 0), "too_far")]:
            with self.assertRaises(BookingError) as cm:
                self.svc.create(self.client, "haircut", "andriy", start, "ai")
            self.assertEqual(cm.exception.code, code)

    def test_any_master_least_loaded(self):
        day = datetime(2026, 10, 27, 12, 0)
        self.svc.create(self.client2, "haircut", "andriy", datetime(2026, 10, 27, 10, 0), "buttons")
        self.assertEqual(self.svc.resolve_master("haircut", "any", day), "oleg")

    def test_any_master_fewest_upcoming_overall(self):
        # В Андрія 27.10 вільно, але загалом у нього 2 майбутні записи, а в Олега — 1 (саме 27.10).
        self.svc.create(self.client2, "haircut", "andriy", datetime(2026, 10, 28, 10, 0), "buttons")
        self.svc.create(self.client2, "haircut", "andriy", datetime(2026, 10, 29, 10, 0), "buttons")
        self.svc.create(self.client, "haircut", "oleg", datetime(2026, 10, 27, 10, 0), "buttons")
        self.assertEqual(self.svc.resolve_master("haircut", "any", datetime(2026, 10, 27, 12, 0)), "oleg")

    def test_any_master_rotates_on_tie(self):
        # Майбутніх записів ні в кого немає; Андрію запис давали нещодавно (потім скасували) — черга Олега.
        self.assertEqual(self.svc.resolve_master("haircut", "any", datetime(2026, 10, 27, 12, 0)), "andriy")
        b = self.svc.create(self.client2, "haircut", "andriy", datetime(2026, 10, 28, 10, 0), "buttons")
        self.svc.cancel(b["id"], "admin")
        self.assertEqual(self.svc.resolve_master("haircut", "any", datetime(2026, 10, 27, 12, 0)), "oleg")

    def test_cancel_rules(self):
        b = self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, 27, 10, 0), "buttons")
        with self.assertRaises(BookingError) as cm:
            self.svc.cancel(b["id"], "client", self.client2)
        self.assertEqual(cm.exception.code, "not_found")
        set_time(2026, 10, 27, 8, 30)  # за 1,5 год — пізно
        with self.assertRaises(BookingError) as cm:
            self.svc.cancel(b["id"], "client", self.client)
        self.assertEqual(cm.exception.code, "too_late")
        self.assertEqual(self.svc.cancel(b["id"], "admin")["status"], "cancelled")  # адміну можна

    def test_reschedule_excludes_itself(self):
        b = self.svc.create(self.client, "haircut", "andriy", datetime(2026, 10, 27, 10, 0), "buttons")
        old, new = self.svc.reschedule(b["id"], datetime(2026, 10, 27, 10, 30), None, self.client)
        self.assertEqual(new["start_at"], "2026-10-27 10:30")
        self.assertEqual(new["master_id"], "andriy")
        with self.assertRaises(BookingError) as cm:
            self.svc.reschedule(b["id"], datetime(2026, 10, 27, 10, 30), None, self.client)
        self.assertEqual(cm.exception.code, "same_time")
        # менше ніж за 2 год клієнт перенести вже не може
        late = self.svc.create(self.client, "beard", "andriy", datetime(2026, 10, 26, 10, 0), "buttons")
        with self.assertRaises(BookingError) as cm:
            self.svc.reschedule(late["id"], datetime(2026, 10, 26, 12, 0), None, self.client)
        self.assertEqual(cm.exception.code, "too_late")

    def test_day_labels(self):
        t = self.tenant
        self.assertEqual(t.day_label(date(2026, 10, 26), "uk"), "Сьогодні, пн 26.10")
        self.assertEqual(t.day_label(date(2026, 10, 27), "uk"), "Завтра, вт 27.10")
        self.assertEqual(t.day_label(date(2026, 10, 28), "uk"), "Ср, 28.10")
        self.assertEqual(t.day_button(date(2026, 10, 28), "en"), "Wed 28.10")
        self.assertEqual(t.day_label(date(2026, 10, 26), "hu"), "Ma, H 26.10")
        self.assertEqual(t.day_button(date(2026, 10, 28), "hu"), "Sze 28.10")
        self.assertEqual(t.day_label(date(2026, 10, 27), "de"), "Morgen, Di 27.10")
        self.assertTrue(re.match(r"^\d{2}:\d{2}$", list(self.svc.free_slots("beard", "any", date(2026, 10, 27)))[0]))


if __name__ == "__main__":
    unittest.main()


class DbFileTests(unittest.TestCase):
    def test_wal_and_fast_sync(self):
        from barberbot.db import DB
        db = DB(Path(tempfile.mkdtemp()) / "bot.db")
        try:
            self.assertEqual(db.scalar("PRAGMA journal_mode"), "wal")
            self.assertEqual(db.scalar("PRAGMA synchronous"), 1)  # NORMAL
        finally:
            db.close()


class CallbackLengthTests(unittest.TestCase):
    EXTRA = """
[[services]]
id = "superlonghaircut"
title = "Довга назва"
duration = 60
price = 600

[[services]]
id = "extraordinarywsh"
title = "Миття"
duration = 15
price = 100
addon_only = true
addon_for = ["superlonghaircut"]

[[masters]]
id = "{master}"
name = "Майстер"
services = ["superlonghaircut", "extraordinarywsh"]
"""

    def test_too_long_ids_rejected(self):
        from .helpers import make_tenant
        # «superlonghaircut+extraordinarywsh» (33) + майстер на 16 символів = 49 > 45.
        with self.assertRaises(ConfigError) as cm:
            make_tenant(extra=self.EXTRA.format(master="verylongmasterid"))
        self.assertIn("кнопки Telegram", str(cm.exception))
        # З коротшим id майстра (33 + 12 = 45) — вміщається.
        t = make_tenant(extra=self.EXTRA.format(master="shortermaster"[:12]))
        self.assertIn("superlonghaircut+extraordinarywsh", t.services)
