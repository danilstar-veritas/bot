"""Адаптер Gemini: переклад запитів і відповідей між форматами Claude і Gemini (без мережі)."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from barberbot import clock
from barberbot.agent import Agent
from barberbot.booking import BookingService
from barberbot.config import load_settings
from barberbot.db import DB
from barberbot.llm import DUMMY_SIGNATURE, GENERATED_ID_PREFIX, ClaudeClient, GeminiClient, make_llm

from .helpers import make_settings, make_tenant, set_time


class FakeGemini(GeminiClient):
    """GeminiClient, у якого замість HTTP — заготовлені відповіді API."""

    def __init__(self, replies: list[dict], model: str = "gemini-3.5-flash"):
        super().__init__("test-key", model)
        self.replies = list(replies)
        self.requests: list[dict] = []

    def _post(self, method: str, payload: dict) -> dict:
        self.requests.append(copy.deepcopy(payload))
        return self.replies.pop(0)


def call_reply(name: str, args: dict, call_id: str | None = "call-1", signature: str | None = "sig-1") -> dict:
    part: dict = {"functionCall": {"name": name, "args": args}}
    if call_id:
        part["functionCall"]["id"] = call_id
    if signature:
        part["thoughtSignature"] = signature
    return {"candidates": [{"content": {"role": "model", "parts": [part]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 1000, "cachedContentTokenCount": 400,
                              "candidatesTokenCount": 20, "thoughtsTokenCount": 30}}


def text_reply(text: str, reason: str = "STOP") -> dict:
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": reason}],
            "usageMetadata": {"promptTokenCount": 1100, "candidatesTokenCount": 15}}


class GeminiAgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        set_time(2026, 10, 26, 9, 0)
        self.tenant = make_tenant()
        self.db = DB(":memory:")
        self.booking = BookingService(self.tenant, self.db)
        self.settings = make_settings()
        self.client = self.db.upsert_client(self.tenant.slug, 100, "Іван", None, "ivan", "uk", self.tenant.now())

    def tearDown(self):
        clock.set_fixed(None)
        self.db.close()

    async def ask(self, llm: GeminiClient, text: str):
        return await Agent(self.settings, llm).reply(self.tenant, self.booking, self.db, self.client, text)

    async def test_tool_loop_round_trip(self):
        llm = FakeGemini([
            call_reply("get_free_slots", {"service_id": "haircut", "master_id": "any", "date": "2026-10-27"}),
            text_reply("Є вільний час завтра 👇"),
        ])
        result = await self.ask(llm, "Хочу на стрижку завтра")
        self.assertIsNone(result.error)
        self.assertEqual(result.tools_used, ["get_free_slots"])
        self.assertEqual(result.text, "Є вільний час завтра 👇")

        first, second = llm.requests
        self.assertIn("Тест Барбер", first["systemInstruction"]["parts"][0]["text"])
        self.assertEqual(first["contents"], [{"role": "user", "parts": [{"text": "Хочу на стрижку завтра"}]}])
        self.assertEqual(first["toolConfig"], {"functionCallingConfig": {"mode": "AUTO"}})
        self.assertEqual(first["generationConfig"]["thinkingConfig"], {"thinkingLevel": "low"})
        decls = {d["name"]: d for d in first["tools"][0]["functionDeclarations"]}
        self.assertNotIn("parameters", decls["get_my_bookings"])  # інструмент без полів
        self.assertEqual(decls["get_free_slots"]["parameters"]["required"], ["service_id"])

        # Виклик повертається з тим самим id і підписом, відповідь інструмента — з id та назвою.
        model_turn, tool_turn = second["contents"][1], second["contents"][2]
        self.assertEqual(model_turn["role"], "model")
        self.assertEqual(model_turn["parts"][0]["thoughtSignature"], "sig-1")
        self.assertEqual(model_turn["parts"][0]["functionCall"]["id"], "call-1")
        response = tool_turn["parts"][0]["functionResponse"]
        self.assertEqual((response["id"], response["name"]), ("call-1", "get_free_slots"))
        self.assertIn("days", response["response"])

    async def test_history_from_old_turn_uses_dummy_signature(self):
        await self.ask(FakeGemini([call_reply("get_my_bookings", {}), text_reply("Записів немає.")]), "Мої записи?")
        # Новий клієнт (наче бот перезапустили) — підписів у пам'яті немає.
        llm = FakeGemini([text_reply("Добре!")])
        await self.ask(llm, "Дякую")
        parts = [p for c in llm.requests[0]["contents"] for p in c["parts"] if "functionCall" in p]
        self.assertEqual(parts[0]["thoughtSignature"], DUMMY_SIGNATURE)

    async def test_call_without_id_older_models(self):
        llm = FakeGemini([call_reply("get_my_bookings", {}, call_id=None, signature=None), text_reply("Немає.")],
                         model="gemini-2.5-flash")
        await self.ask(llm, "Мої записи?")
        second = llm.requests[1]
        self.assertEqual(second["generationConfig"]["thinkingConfig"], {"thinkingBudget": 1024})
        call = second["contents"][1]["parts"][0]["functionCall"]
        response = second["contents"][2]["parts"][0]["functionResponse"]
        self.assertNotIn("id", call)
        self.assertNotIn("id", response)
        self.assertEqual(response["name"], "get_my_bookings")


class GeminiResponseTests(unittest.TestCase):
    def setUp(self):
        self.llm = GeminiClient("k", "gemini-3.5-flash")

    def test_usage_and_tool_use(self):
        out = self.llm._response(call_reply("get_my_bookings", {}))
        self.assertEqual(out["stop_reason"], "tool_use")
        self.assertEqual(out["usage"], {"input_tokens": 600, "output_tokens": 50, "cache_read_input_tokens": 400,
                                        "cache_creation_input_tokens": 0})

    def test_generated_id_when_missing(self):
        out = self.llm._response(call_reply("get_my_bookings", {}, call_id=None))
        self.assertTrue(out["content"][0]["id"].startswith(GENERATED_ID_PREFIX))

    def test_stop_reasons(self):
        self.assertEqual(self.llm._response(text_reply("...", "MAX_TOKENS"))["stop_reason"], "max_tokens")
        self.assertEqual(self.llm._response(text_reply("", "SAFETY"))["stop_reason"], "refusal")
        blocked = self.llm._response({"promptFeedback": {"blockReason": "SAFETY"}})
        self.assertEqual((blocked["stop_reason"], blocked["content"]), ("refusal", []))

    def test_thought_parts_skipped(self):
        data = text_reply("Відповідь")
        data["candidates"][0]["content"]["parts"].insert(0, {"text": "міркування", "thought": True})
        self.assertEqual(self.llm._response(data)["content"], [{"type": "text", "text": "Відповідь"}])

    def test_tool_choice_none(self):
        request = self.llm._request({"messages": [{"role": "user", "content": "x"}],
                                     "tools": [{"name": "t", "input_schema": {"type": "object", "properties": {}}}],
                                     "tool_choice": {"type": "none"}})
        self.assertEqual(request["toolConfig"], {"functionCallingConfig": {"mode": "NONE"}})


class GeminiSettingsTests(unittest.TestCase):
    def write(self, text: str) -> Path:
        path = Path(tempfile.mkdtemp()) / "settings.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_gemini_provider(self):
        s = load_settings(self.write('provider = "gemini"\ngemini_api_key = "AIza-test"\n'))
        self.assertTrue(s.ai_available)
        self.assertEqual((s.ai_name, s.ai_model), ("Gemini", "gemini-3.5-flash"))
        self.assertEqual((s.price_input, s.price_output), (0.0, 0.0))
        self.assertIsInstance(make_llm(s), GeminiClient)

    def test_gemini_without_key_is_not_available(self):
        s = load_settings(self.write('provider = "gemini"\nanthropic_api_key = "sk-ant-x"\n'))
        self.assertFalse(s.ai_available)

    def test_default_is_anthropic(self):
        s = load_settings(self.write('anthropic_api_key = "sk-ant-x"\n'))
        self.assertEqual(s.ai_name, "Anthropic")
        self.assertEqual(s.price_input, 0.10)
        self.assertIsInstance(make_llm(s), ClaudeClient)


if __name__ == "__main__":
    unittest.main()
