"""Переклади даних закладу (title_en, about_de, directions_en…) і вибір мови клієнта."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from barberbot.app import BotApp
from barberbot.config import ConfigError, load_tenant
from barberbot.db import DB

from .helpers import ADMIN_ID, CLIENT_ID, TENANT_TOML, TOKEN, FakeLLM, FakeTelegram, cb, make_settings, msg, set_time

TRANSLATED = {
    'title = "Чоловіча стрижка"\n': 'title = "Чоловіча стрижка"\ntitle_en = "Men\'s haircut"\n'
                                    'description = "З укладанням."\ndescription_en = "Styling included."\n',
    'title = "Борода"\n': 'title = "Борода"\ntitle_en = "Beard"\n',
    'name = "Андрій"\n': 'name = "Андрій"\nname_en = "Andrii"\nabout = "Майстер фейдів."\nabout_en = "Fade master."\n',
    'payment = "Готівка або картка"\n': 'payment = "Готівка або картка"\npayment_en = "Cash or card"\n'
                                        'directions = "Вхід з двору."\ndirections_en = "Entrance from the yard."\n',
}


def make_translated_tenant(languages: str = '["uk", "en"]', extra: dict | None = None):
    text = TENANT_TOML.format(token=TOKEN, admin=ADMIN_ID, require_phone="false")
    text = text.replace('languages = ["uk", "ru", "en", "hu", "de"]', f"languages = {languages}")
    for old, new in {**TRANSLATED, **(extra or {})}.items():
        assert old in text, old
        text = text.replace(old, new, 1)
    path = Path(tempfile.mkdtemp()) / "i18n-barber.toml"
    path.write_text(text, encoding="utf-8")
    return load_tenant(path)


class LanguageChoiceTests(unittest.TestCase):
    def test_unlisted_language_falls_back_to_english(self):
        t = make_translated_tenant('["hu", "uk", "en"]')
        self.assertEqual(t.lang_for("uk"), "uk")
        self.assertEqual(t.lang_for("ru"), "en")
        self.assertEqual(t.lang_for("pt-br"), "en")
        self.assertEqual(t.lang_for(None), "hu")  # мова невідома — основна мова закладу

    def test_without_english_falls_back_to_main_language(self):
        t = make_translated_tenant('["uk", "ru"]')
        self.assertEqual(t.lang_for("de"), "uk")

    def test_translations_parsed(self):
        t = make_translated_tenant()
        haircut = t.services["haircut"]
        self.assertEqual(haircut.tr("title", "en"), "Men's haircut")
        self.assertEqual(haircut.tr("title", "uk"), "Чоловіча стрижка")
        self.assertEqual(haircut.tr("title", "de"), "Чоловіча стрижка")  # перекладу немає — базова назва
        self.assertEqual(t.masters["andriy"].tr("name", "en"), "Andrii")
        self.assertEqual(t.info_in("directions", "en"), "Entrance from the yard.")
        self.assertEqual(t.info_in("directions", "uk"), "Вхід з двору.")

    def test_unsupported_translation_language(self):
        with self.assertRaises(ConfigError) as cm:
            make_translated_tenant(extra={'title = "Борода"\n': 'title = "Борода"\ntitle_xx = "?"\n'})
        self.assertIn("title_xx", str(cm.exception))


class TranslatedClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        set_time(2026, 10, 26, 9, 0)
        self.tenant = make_translated_tenant()
        self.db = DB(":memory:")
        self.tg = FakeTelegram()
        self.app = BotApp(make_settings(), [self.tenant], self.db, FakeLLM(), api_factory=lambda t: self.tg)

    async def asyncTearDown(self):
        self.db.close()

    async def send(self, update: dict) -> None:
        await self.app.handle_update(self.tenant.slug, update)

    def last(self, uid: int = CLIENT_ID) -> dict:
        return self.tg.last(uid)

    async def test_english_client_sees_translated_data(self):
        await self.send(msg(text="💈 Services & prices", lang="en"))
        prices = self.last()["text"]
        self.assertIn("<b>Men's haircut</b>", prices)
        self.assertIn("Styling included.", prices)
        self.assertNotIn("Чоловіча", prices)

        await self.send(msg(text="📍 Contacts", lang="en"))
        contacts = self.last()["text"]
        self.assertIn("Entrance from the yard.", contacts)
        self.assertIn("Cash or card", contacts)
        self.assertIn("<b>Andrii</b>\n<i>Fade master.</i>", contacts)

        await self.send(cb("bs:haircut", lang="en"))
        self.assertIn("💈 <b>Men's haircut</b>", self.last()["text"])
        self.assertIn(("Andrii", "bm:haircut:andriy"),
                      [(b["text"], b["callback_data"]) for b in self.tg.buttons(self.last())])

        await self.send(cb("bc:haircut:andriy:20261027:1200", lang="en"))
        booked = self.last()["text"]
        self.assertIn("💈 Men's haircut\n👤 Andrii", booked)
        b = self.db.get_booking(1)
        self.assertEqual((b["service_title"], b["master_name"]), ("Чоловіча стрижка", "Андрій"))  # в базі — основна мова
        self.assertIn("Men's haircut", self.app.reminder_text(self.tenant, b, "en"))

        await self.send(msg(text="🗓 My bookings", lang="en"))
        self.assertIn("✂️ Men's haircut\n💈 Master: Andrii", self.last()["text"])

    async def test_admin_sees_main_language(self):
        await self.send(cb("bc:haircut:andriy:20261027:1200", lang="en"))
        admin_note = self.last(ADMIN_ID)["text"]
        self.assertIn("Чоловіча стрижка · Андрій", admin_note)

    async def test_unlisted_language_client_gets_english(self):
        await self.send(msg(text="/start", lang="pl"))
        kb = self.last()["reply_markup"]["keyboard"]
        self.assertEqual(kb[0][0]["text"], "📅 Book")


if __name__ == "__main__":
    unittest.main()
