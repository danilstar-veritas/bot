"""AI-агент: цикл інструментів, історія, безпека дій (з фейковою моделлю)."""

from __future__ import annotations

import json
import unittest
from datetime import datetime

from barberbot import clock
from barberbot.agent import Agent, merge_roles, prepare_history
from barberbot.booking import BookingService
from barberbot.db import DB
from barberbot.llm import LLMError

from .helpers import FakeLLM, last_tool_result, make_settings, make_tenant, set_time, text_reply, tool_call


def pick_first_slot(payload: dict) -> dict:
    result = last_tool_result(payload)
    day = result["days"][0]
    time_, masters = next(iter(day["times"].items()))
    return tool_call(("create_booking", {"service_id": "haircut", "master_id": masters[0],
                                         "date": day["date"], "time": time_}))


class AgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        set_time(2026, 10, 26, 9, 0)
        self.tenant = make_tenant()
        self.db = DB(":memory:")
        self.booking = BookingService(self.tenant, self.db)
        self.settings = make_settings()
        self.client = self.db.upsert_client(self.tenant.slug, 100, "Іван", None, "ivan", "uk", self.tenant.now())
        self.other = self.db.upsert_client(self.tenant.slug, 200, "Петро", None, None, "uk", self.tenant.now())

    def tearDown(self):
        clock.set_fixed(None)
        self.db.close()

    async def ask(self, llm: FakeLLM, text: str):
        agent = Agent(self.settings, llm)
        return await agent.reply(self.tenant, self.booking, self.db, self.client, text)

    async def test_booking_flow_creates_only_a_proposal(self):
        llm = FakeLLM([
            tool_call(("get_free_slots", {"service_id": "haircut", "master_id": "any", "date": "2026-10-27",
                                          "time_from": "17:00"})),
            pick_first_slot,
            text_reply("Перевірте, будь ласка, і натисніть «Підтвердити» 👇"),
        ])
        result = await self.ask(llm, "Хочу на стрижку завтра ввечері")
        self.assertIsNone(result.error)
        self.assertEqual(result.tools_used, ["get_free_slots", "create_booking"])
        self.assertEqual(len(result.effects), 1)
        effect = result.effects[0]
        self.assertEqual(effect["type"], "confirm_booking")
        self.assertEqual(effect["start"], datetime(2026, 10, 27, 17, 0))
        self.assertIn("Підтвердити", result.text)
        # Запис НЕ створено — лише пропозиція
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM bookings"), 0)

        # Перевірка запиту до API
        first, second = llm.payloads[0], llm.payloads[1]
        self.assertEqual(first["model"], "claude-haiku-5-5")
        self.assertNotIn("temperature", first)
        self.assertEqual(first["output_config"], {"effort": "low"})
        self.assertEqual(first["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertIn("Тест Барбер", first["system"][0]["text"])
        self.assertIn("2026-10-27 (завтра)", first["system"][1]["text"])
        self.assertNotIn("tool_choice", first)
        self.assertEqual({t["name"] for t in first["tools"]},
                         {"get_free_slots", "create_booking", "get_my_bookings", "cancel_booking",
                          "reschedule_booking", "save_client_contact", "handoff_to_owner"})
        # thinking-блок повертається в циклі без змін
        assistant = second["messages"][-2]
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["content"][0], {"type": "thinking", "thinking": "", "signature": "sig-abc"})
        slots = last_tool_result(second)
        self.assertTrue(all(t >= "17:00" for t in slots["days"][0]["times"]))

        # Історія збережена без thinking-блоків
        rows = self.db.q("SELECT role, content FROM history ORDER BY id")
        self.assertEqual([r["role"] for r in rows], ["user", "assistant", "user", "assistant", "user", "assistant"])
        self.assertNotIn("thinking", " ".join(r["content"] for r in rows))

        # Наступний хід бачить попередні інструменти, а повідомлення чергуються
        llm.add(text_reply("Будь ласка!"))
        await self.ask(llm, "Дякую")
        messages = llm.payloads[-1]["messages"]
        roles = [m["role"] for m in messages]
        self.assertEqual(roles[0], "user")
        self.assertTrue(all(a != b for a, b in zip(roles, roles[1:])))
        self.assertEqual(messages[-1]["content"], "Дякую")

    async def test_tool_errors_are_reported_to_model(self):
        self.booking.create(self.other["id"], "haircut", "andriy", datetime(2026, 10, 26, 12, 0), "buttons")
        llm = FakeLLM([
            tool_call(("create_booking", {"service_id": "haircut", "master_id": "andriy", "date": "2026-10-26",
                                          "time": "12:00"})),
            text_reply("На жаль, 12:00 уже зайнято."),
        ])
        result = await self.ask(llm, "Запишіть до Андрія сьогодні на 12")
        self.assertEqual(result.effects, [])
        block = llm.payloads[1]["messages"][-1]["content"][0]
        self.assertTrue(block["is_error"])
        self.assertEqual(json.loads(block["content"])["error"], "slot_taken")

    async def test_cannot_touch_other_clients_booking(self):
        foreign = self.booking.create(self.other["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "ai")
        llm = FakeLLM([
            tool_call(("cancel_booking", {"booking_id": foreign["id"]})),
            text_reply("Не знайшов такого запису."),
        ])
        result = await self.ask(llm, f"Скасуйте запис №{foreign['id']}")
        self.assertEqual(result.effects, [])
        self.assertEqual(last_tool_result(llm.payloads[1])["error"], "not_found")
        self.assertEqual(self.db.get_booking(foreign["id"])["status"], "active")

    async def test_cancel_and_reschedule_proposals(self):
        b = self.booking.create(self.client["id"], "haircut", "andriy", datetime(2026, 10, 27, 12, 0), "ai")
        llm = FakeLLM([
            tool_call(("get_my_bookings", {})),
            lambda p: tool_call(("reschedule_booking", {"booking_id": last_tool_result(p)["bookings"][0]["booking_id"],
                                                        "date": "2026-10-28", "time": "15:00"})),
            text_reply("Натисніть «Перенести», щоб підтвердити."),
        ])
        result = await self.ask(llm, "Перенесіть мій запис на середу о 15")
        self.assertEqual(result.effects[0]["type"], "confirm_reschedule")
        self.assertEqual(result.effects[0]["booking_id"], b["id"])
        self.assertEqual(result.effects[0]["start"], datetime(2026, 10, 28, 15, 0))
        self.assertEqual(self.db.get_booking(b["id"])["start_at"], "2026-10-27 12:00")  # ще не змінено

        llm.add(tool_call(("cancel_booking", {"booking_id": b["id"]})), text_reply("Підтвердіть скасування."))
        result = await self.ask(llm, "Ні, краще скасуйте")
        self.assertEqual(result.effects, [{"type": "confirm_cancel", "booking_id": b["id"]}])
        self.assertEqual(self.db.get_booking(b["id"])["status"], "active")

    async def test_handoff_and_contact(self):
        llm = FakeLLM([
            tool_call(("save_client_contact", {"phone": "дзвоніть мені"}),
                      ("save_client_contact", {"name": "Іван Петрович", "phone": "+380 50 123 45 67"})),
            tool_call(("handoff_to_owner", {"reason": "Просить знижку", "summary": "Хоче -20% для двох"})),
            text_reply("Передав адміністратору, він відповість тут."),
        ])
        result = await self.ask(llm, "Дайте знижку, мій номер +380501234567")
        self.assertEqual(result.effects, [{"type": "handoff", "reason": "Просить знижку",
                                           "summary": "Хоче -20% для двох"}])
        client = self.db.get_client(self.client["id"])
        self.assertEqual(client["phone"], "+380501234567")
        self.assertEqual(client["name"], "Іван Петрович")
        results = llm.payloads[1]["messages"][-1]["content"]
        self.assertEqual(json.loads(results[0]["content"])["error"], "bad_phone")
        self.assertTrue(json.loads(results[1]["content"])["ok"])

    async def test_errors_refusal_and_round_limit(self):
        result = await self.ask(FakeLLM([LLMError("HTTP 529: Overloaded", 529)]), "Привіт")
        self.assertIn("529", result.error)
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM history"), 0)

        refusal = {"content": [], "stop_reason": "refusal", "usage": {}}
        result = await self.ask(FakeLLM([refusal]), "...")
        self.assertTrue(result.refusal)

        self.settings.max_tool_rounds = 2
        llm = FakeLLM([tool_call(("get_my_bookings", {}))] * 2 + [text_reply("Готово")])
        result = await self.ask(llm, "Покажи мої записи")
        self.assertEqual(result.text, "Готово")
        self.assertEqual(llm.payloads[-1]["tool_choice"], {"type": "none"})

        llm = FakeLLM([tool_call(("format_disk", {})), text_reply("Не можу.")])
        await self.ask(llm, "rm -rf")
        self.assertEqual(last_tool_result(llm.payloads[1])["error"], "unknown_tool")

    async def test_markdown_is_cleaned(self):
        result = await self.ask(FakeLLM([text_reply("## Ціни\n**Стрижка** — 500 грн")]), "Ціни?")
        self.assertEqual(result.text, "Ціни\nСтрижка — 500 грн")

    def test_prepare_history_trims_broken_parts(self):
        tool_use = {"type": "tool_use", "id": "t1", "name": "get_my_bookings", "input": {}}
        history = [
            {"role": "assistant", "content": [{"type": "text", "text": "старе"}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t0", "content": "{}"}]},
            {"role": "user", "content": "Привіт"},
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "", "signature": "s"},
                                              {"type": "text", "text": "Вітаю!"}]},
            {"role": "user", "content": "Мої записи?"},
            {"role": "assistant", "content": [tool_use]},
        ]
        cleaned = prepare_history(history)
        self.assertEqual(cleaned[0], {"role": "user", "content": "Привіт"})
        self.assertEqual(cleaned[1]["content"], [{"type": "text", "text": "Вітаю!"}])
        self.assertEqual(len(cleaned), 3)  # tool_use без результату відкинуто
        merged = merge_roles([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])
        self.assertEqual(merged, [{"role": "user", "content": [{"type": "text", "text": "a"},
                                                                {"type": "text", "text": "b"}]}])


if __name__ == "__main__":
    unittest.main()
