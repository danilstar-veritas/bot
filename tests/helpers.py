"""Спільні інструменти для тестів: тестовий заклад, фейковий Telegram і фейкова модель."""

from __future__ import annotations

import asyncio
import copy
import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from barberbot import clock
from barberbot.config import Settings, load_tenant

TOKEN = "123456789:" + "A" * 35
TOKEN2 = "987654321:" + "B" * 35
ADMIN_ID = 500
CLIENT_ID = 100
KYIV = ZoneInfo("Europe/Kyiv")

TENANT_TOML = """
name = "Тест Барбер"
bot_token = "{token}"
admins = [{admin}]
timezone = "Europe/Kyiv"
languages = ["uk", "ru", "en", "hu"]
price_format = "{{price}} грн"

[info]
address = "вул. Тестова, 1"
phone = "+380 00 000 00 00"
maps_url = "https://maps.example.com"
payment = "Готівка або картка"
extra = "Є кава."

[booking]
slot_step_min = 30
days_ahead = 14
min_lead_min = 60
buffer_min = 0
require_phone = {require_phone}
max_active_per_client = 2
cancel_min_hours = 2
holidays = []

[reminders]
hours_before = [24, 2]

[repeat_visit]
enabled = true
after_days = 28
send_at = "11:00"

[notifications]
new_bookings = true
digest_at = "09:00"

[ai]
enabled = true
address_form = "ви"
handoff_pause_hours = 12
max_messages_per_hour = 5
max_messages_per_day = 20

[schedule]
mon = "10:00-19:00"
tue = "10:00-19:00"
wed = "10:00-19:00"
thu = "10:00-19:00"
fri = "10:00-19:00"
sat = "10:00-16:00"
sun = "off"

[[services]]
id = "haircut"
title = "Чоловіча стрижка"
duration = 60
price = 500

[[services]]
id = "beard"
title = "Борода"
duration = 30
price = 300

[[services]]
id = "combo"
title = "Стрижка + борода"
duration = 90
price = 750

[[masters]]
id = "andriy"
name = "Андрій"
services = ["*"]

[[masters]]
id = "oleg"
name = "Олег"
services = ["haircut", "beard"]
  [masters.schedule]
  mon = "off"
"""


def make_tenant(require_phone: bool = True, slug: str = "test-barber", token: str = TOKEN, extra: str = ""):
    tmp = Path(tempfile.mkdtemp())
    path = tmp / f"{slug}.toml"
    text = TENANT_TOML.format(token=token, admin=ADMIN_ID, require_phone="true" if require_phone else "false")
    path.write_text(text + extra, encoding="utf-8")
    return load_tenant(path)


def set_time(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> None:
    """Заморозити «зараз» як місцевий час Києва."""
    clock.set_fixed(datetime(year, month, day, hour, minute, tzinfo=KYIV))


def make_settings(**kw) -> Settings:
    s = Settings(anthropic_api_key="sk-test", data_dir=Path(tempfile.mkdtemp()))
    for k, v in kw.items():
        setattr(s, k, v)
    return s


# ------------------------------------------------------------------ fake Telegram

class FakeTelegram:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.next_id = 1000
        self.fail: dict[str, Exception] = {}

    async def call(self, method: str, _timeout: float = 30, _retries: int = 2, **params):
        params = {k: v for k, v in params.items() if v is not None}
        self.calls.append((method, copy.deepcopy(params)))
        if method in self.fail:
            raise self.fail.pop(method)
        if method == "sendMessage":
            self.next_id += 1
            return {"message_id": self.next_id, "chat": {"id": params["chat_id"]}, "text": params.get("text")}
        if method == "copyMessage":
            self.next_id += 1
            return {"message_id": self.next_id}
        if method == "getMe":
            return {"id": 123456789, "is_bot": True, "username": "test_barber_bot"}
        if method == "getUpdates":
            await asyncio.sleep(0.01)
            return []
        return True

    async def send_document(self, chat_id: int, filename: str, content: bytes, caption: str | None = None,
                            mime: str = "application/octet-stream"):
        self.calls.append(("sendDocument", {"chat_id": chat_id, "filename": filename, "content": content,
                                            "caption": caption, "mime": mime}))
        self.next_id += 1
        return {"message_id": self.next_id}

    def of(self, method: str, chat_id: int | None = None) -> list[dict]:
        return [p for m, p in self.calls if m == method and (chat_id is None or p.get("chat_id") == chat_id)]

    def texts(self, chat_id: int | None = None) -> list[str]:
        """Тексти, надіслані або відредаговані в чаті."""
        return [p.get("text", "") for m, p in self.calls
                if m in ("sendMessage", "editMessageText") and (chat_id is None or p.get("chat_id") == chat_id)]

    def last(self, chat_id: int | None = None) -> dict:
        items = [p for m, p in self.calls if m in ("sendMessage", "editMessageText")
                 and (chat_id is None or p.get("chat_id") == chat_id)]
        return items[-1] if items else {}

    def buttons(self, params: dict) -> list[dict]:
        markup = params.get("reply_markup") or {}
        return [b for row in markup.get("inline_keyboard", []) for b in row]

    def button(self, params: dict, startswith: str) -> dict:
        for b in self.buttons(params):
            if b.get("callback_data", "").startswith(startswith):
                return b
        raise AssertionError(f"Немає кнопки {startswith!r} у {self.buttons(params)}")

    def clear(self) -> None:
        self.calls.clear()


# ------------------------------------------------------------------ fake LLM

def tool_call(*calls: tuple[str, dict]) -> dict:
    content = [{"type": "thinking", "thinking": "", "signature": "sig-abc"}]
    for i, (name, args) in enumerate(calls):
        content.append({"type": "tool_use", "id": f"toolu_{name}_{i}_{id(args)}", "name": name, "input": args})
    return {"content": content, "stop_reason": "tool_use",
            "usage": {"input_tokens": 1200, "output_tokens": 60, "cache_read_input_tokens": 3000,
                      "cache_creation_input_tokens": 0}}


def text_reply(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
            "usage": {"input_tokens": 1300, "output_tokens": 40}}


def last_tool_result(payload: dict) -> dict:
    """Результат останнього інструмента з повідомлень, які бот надіслав моделі."""
    for message in reversed(payload["messages"]):
        if message["role"] == "user" and isinstance(message["content"], list):
            for block in reversed(message["content"]):
                if block.get("type") == "tool_result":
                    return json.loads(block["content"])
    raise AssertionError("tool_result не знайдено")


class FakeLLM:
    def __init__(self, script=None):
        self.script = list(script or [])
        self.payloads: list[dict] = []

    def add(self, *steps) -> None:
        self.script.extend(steps)

    async def create(self, payload: dict) -> dict:
        self.payloads.append(copy.deepcopy(payload))
        if not self.script:
            raise AssertionError("FakeLLM: сценарій закінчився")
        step = self.script.pop(0)
        if callable(step):
            step = step(payload)
        if isinstance(step, Exception):
            raise step
        return step


# ------------------------------------------------------------------ updates

_update_id = 0


def _next_id() -> int:
    global _update_id
    _update_id += 1
    return _update_id


def user(uid: int = CLIENT_ID, name: str = "Іван", lang: str = "uk", username: str | None = "ivan") -> dict:
    u = {"id": uid, "is_bot": False, "first_name": name, "language_code": lang}
    if username:
        u["username"] = username
    return u


def msg(uid: int = CLIENT_ID, text: str | None = None, lang: str = "uk", **extra) -> dict:
    m = {"message_id": _next_id(), "date": 0, "chat": {"id": uid, "type": "private"},
         "from": user(uid, "Адмін" if uid == ADMIN_ID else "Іван", lang)}
    if text is not None:
        m["text"] = text
    m.update(extra)
    return {"update_id": _next_id(), "message": m}


def cb(data: str, uid: int = CLIENT_ID, message_id: int = 777, lang: str = "uk") -> dict:
    return {"update_id": _next_id(), "callback_query": {
        "id": f"cb{_next_id()}", "from": user(uid, "Адмін" if uid == ADMIN_ID else "Іван", lang),
        "data": data, "message": {"message_id": message_id, "chat": {"id": uid, "type": "private"}}}}
