"""Справжній HTTP: локальні сервери, що імітують Telegram Bot API і Claude API.

Перевіряє весь стек: long polling, JSON-запити, повтори при 529, два заклади в одному процесі,
а також команди run.py check / eval.
"""

from __future__ import annotations

import asyncio
import io
import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from barberbot import cli, clock
from barberbot.app import BotApp
from barberbot.config import load_tenant
from barberbot.db import DB
from barberbot.llm import ClaudeClient
from barberbot.telegram import TelegramAPI

from .helpers import (ADMIN_ID, CLIENT_ID, TENANT_TOML, TOKEN, TOKEN2, FakeLLM, cb, make_settings, msg, set_time,
                      text_reply, tool_call)


class FakeServers:
    """Один HTTP-сервер: /bot<token>/<method> — Telegram, /v1/messages — Claude."""

    def __init__(self):
        self.lock = threading.Lock()
        self.updates: dict[str, list[dict]] = {}
        self.calls: list[tuple[str, str, dict]] = []
        self.claude_requests: list[tuple[dict, dict]] = []
        self.claude_script: list = []
        self.next_message_id = 5000
        servers = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path.startswith("/v1/messages"):
                    status, payload = servers.claude(self.path, dict(self.headers), body)
                else:
                    _, token_part, method = self.path.split("/", 2)
                    status, payload = 200, servers.telegram(token_part[3:], method, body)
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    # -------------------------------------------------- Telegram
    def push(self, token: str, update: dict) -> None:
        with self.lock:
            self.updates.setdefault(token, []).append(update)

    def telegram(self, token: str, method: str, body: dict) -> dict:
        if token not in (TOKEN, TOKEN2):
            return {"ok": False, "error_code": 401, "description": "Unauthorized"}
        if method == "getUpdates":
            deadline = time.time() + min(float(body.get("timeout", 0)), 0.3)
            while True:
                with self.lock:
                    pending = [u for u in self.updates.get(token, []) if u["update_id"] >= (body.get("offset") or 0)]
                if pending or time.time() >= deadline:
                    return {"ok": True, "result": pending}
                time.sleep(0.02)
        with self.lock:
            self.calls.append((token, method, body))
        if method == "getMe":
            return {"ok": True, "result": {"id": int(token.split(":")[0]), "is_bot": True,
                                           "username": f"bot{token[:3]}"}}
        if method in ("sendMessage", "copyMessage"):
            with self.lock:
                self.next_message_id += 1
                return {"ok": True, "result": {"message_id": self.next_message_id,
                                               "chat": {"id": body["chat_id"]}, "text": body.get("text")}}
        if method == "editMessageText" and body.get("message_id") == 1:
            return {"ok": False, "error_code": 400, "description": "Bad Request: message is not modified"}
        return {"ok": True, "result": True}

    def sent(self, token: str, chat_id: int, method: str = "sendMessage") -> list[dict]:
        with self.lock:
            return [b for t, m, b in self.calls if t == token and m == method and b.get("chat_id") == chat_id]

    # -------------------------------------------------- Claude
    def claude(self, path: str, headers: dict, body: dict) -> tuple[int, dict]:
        lower = {k.lower(): v for k, v in headers.items()}
        with self.lock:
            self.claude_requests.append((lower, body))
        if lower.get("x-api-key") != "sk-test" or lower.get("anthropic-version") != "2023-06-01":
            return 401, {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}
        if path.endswith("/count_tokens"):
            return 200, {"input_tokens": 1777}
        with self.lock:
            step = self.claude_script.pop(0) if self.claude_script else None
        if step is None:
            return 500, {"type": "error", "error": {"type": "api_error", "message": "script empty"}}
        if callable(step):
            step = step(body)
        if isinstance(step, tuple):
            return step
        return 200, step


async def wait_for(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Не дочекалися очікуваної події")


class HttpEndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        set_time(2026, 10, 26, 9, 0)
        self.srv = FakeServers()
        tmp = Path(tempfile.mkdtemp())
        (tmp / "first.toml").write_text(TENANT_TOML.format(token=TOKEN, admin=ADMIN_ID, require_phone="false"),
                                        encoding="utf-8")
        second = TENANT_TOML.format(token=TOKEN2, admin=ADMIN_ID, require_phone="false")
        (tmp / "second.toml").write_text(second.replace('name = "Тест Барбер"', 'name = "Другий Барбер"'),
                                         encoding="utf-8")
        self.t1, self.t2 = load_tenant(tmp / "first.toml"), load_tenant(tmp / "second.toml")
        self.settings = make_settings(telegram_api_base=self.srv.base, anthropic_api_base=self.srv.base)
        self.db = DB(":memory:")
        llm = ClaudeClient("sk-test", self.srv.base, timeout=5)
        self.app = BotApp(self.settings, [self.t1, self.t2], self.db, llm,
                          api_factory=lambda t: TelegramAPI(t.bot_token, self.srv.base))
        self.app.poll_timeout = 1
        self.task = asyncio.create_task(self.app.run())

    async def asyncTearDown(self):
        self.app.stop()
        started = time.monotonic()
        await asyncio.wait_for(self.task, timeout=5)
        self.assertLess(time.monotonic() - started, 3, "бот має зупинятися швидко")
        self.srv.close()
        self.db.close()
        clock.set_fixed(None)

    async def test_two_bots_buttons_and_ai(self):
        srv = self.srv
        await wait_for(lambda: len([c for c in srv.calls if c[1] == "setMyCommands"]) >= 2)

        srv.push(TOKEN, msg(text="/start"))
        srv.push(TOKEN2, msg(text="/start"))
        await wait_for(lambda: srv.sent(TOKEN, CLIENT_ID) and srv.sent(TOKEN2, CLIENT_ID))
        self.assertIn("Тест Барбер", srv.sent(TOKEN, CLIENT_ID)[0]["text"])
        self.assertIn("Другий Барбер", srv.sent(TOKEN2, CLIENT_ID)[0]["text"])

        # Кнопки: callback → editMessageText + answerCallbackQuery
        srv.push(TOKEN, cb("bs:haircut", message_id=1))  # «message is not modified» не ламає бота
        srv.push(TOKEN, cb("bm:haircut:andriy", message_id=42))
        await wait_for(lambda: len(srv.sent(TOKEN, CLIENT_ID, "editMessageText")) >= 2)
        await wait_for(lambda: len([c for c in srv.calls if c[1] == "answerCallbackQuery"]) >= 2)
        days = srv.sent(TOKEN, CLIENT_ID, "editMessageText")[-1]
        self.assertEqual(days["reply_markup"]["inline_keyboard"][0][0]["callback_data"], "bd:haircut:andriy:20261026")

        # AI: спершу перевантаження 529 (повтор), потім інструмент, потім відповідь
        srv.claude_script += [
            (529, {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}),
            tool_call(("get_free_slots", {"service_id": "beard", "master_id": "any", "date": "2026-10-27"})),
            text_reply("Завтра є вільний час з 10:00 🙂"),
        ]
        srv.push(TOKEN, msg(text="Коли можна на бороду завтра?"))
        await wait_for(lambda: any("Завтра є вільний" in m.get("text", "") for m in srv.sent(TOKEN, CLIENT_ID)),
                       timeout=10)
        reply = [m for m in srv.sent(TOKEN, CLIENT_ID) if "Завтра є вільний" in m.get("text", "")][0]
        self.assertNotIn("parse_mode", reply)
        self.assertEqual(len(srv.claude_requests), 3)
        headers, body = srv.claude_requests[-1]
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(body["model"], "claude-haiku-5-5")
        tool_result = body["messages"][-1]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        self.assertIn("10:00", tool_result["content"])
        self.assertTrue(srv.sent(TOKEN, CLIENT_ID, "sendChatAction"))
        # Події записані в базу
        self.assertGreaterEqual(self.db.count_events(self.t1.slug, "ai_usage", self.t1.now().replace(hour=0)), 2)


class CliTests(unittest.TestCase):
    def setUp(self):
        set_time(2026, 10, 26, 9, 0)
        self.srv = FakeServers()
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "tenants").mkdir()
        (self.tmp / "tenants" / "shop.toml").write_text(
            TENANT_TOML.format(token=TOKEN, admin=ADMIN_ID, require_phone="true"), encoding="utf-8")
        (self.tmp / "settings.toml").write_text(
            f'anthropic_api_key = "sk-test"\n[advanced]\ntelegram_api_base = "{self.srv.base}"\n'
            f'anthropic_api_base = "{self.srv.base}"\ndata_dir = "{self.tmp / "data"}"\n', encoding="utf-8")
        self.saved = (cli.SETTINGS_PATH, cli.TENANTS_DIR, cli.CONFIG_DIR)
        cli.SETTINGS_PATH, cli.TENANTS_DIR, cli.CONFIG_DIR = self.tmp / "settings.toml", self.tmp / "tenants", self.tmp

    def tearDown(self):
        cli.SETTINGS_PATH, cli.TENANTS_DIR, cli.CONFIG_DIR = self.saved
        self.srv.close()
        clock.set_fixed(None)

    def run_cli(self, fn, *args, **kw) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = fn(*args, **kw)
        return code, out.getvalue()

    def test_check_ok(self):
        code, out = self.run_cli(cli.cmd_check)
        self.assertEqual(code, 0, out)
        self.assertIn("токен правильний", out)
        self.assertIn("Ключ Anthropic працює", out)
        self.assertIn("~1777 токенів", out)
        self.assertIn("Найближчий вільний час", out)

    def test_check_reports_bad_key(self):
        settings = self.tmp / "settings.toml"
        settings.write_text(settings.read_text(encoding="utf-8").replace("sk-test", "sk-wrong"), encoding="utf-8")
        code, out = self.run_cli(cli.cmd_check)
        self.assertEqual(code, 1)
        self.assertIn("invalid x-api-key", out)

    def test_backup_keeps_last_copies(self):
        import os
        import sqlite3
        db = DB(self.tmp / "data" / "bot.db")
        db.log_event("shop", None, "msg_in", clock.utcnow().replace(tzinfo=None))
        db.close()
        for _ in range(3):
            code, out = self.run_cli(cli.cmd_backup, ["2"])
            self.assertEqual(code, 0, out)
            time.sleep(0.02)
        copies = sorted((self.tmp / "data" / "backups").glob("bot-*.db"))
        self.assertEqual(len(copies), 2)
        for c in copies:
            self.assertEqual(oct(os.stat(c).st_mode & 0o777), "0o640")
            con = sqlite3.connect(c)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)
            con.close()

    def test_eval_runner(self):
        scenarios = self.tmp / "eval.toml"
        scenarios.write_text("""
[[scenario]]
name = "Знижка"
messages = ["Дайте знижку"]
expect_tools = ["handoff_to_owner"]

[[scenario]]
name = "Запис із підтвердженням"
confirm_cards = true
messages = ["Запишіть на бороду 27.10 о 10:00"]
expect_effects = ["confirm_booking"]
must_not_contain = ["ви записані"]
""", encoding="utf-8")
        llm = FakeLLM([
            tool_call(("handoff_to_owner", {"reason": "Знижка", "summary": "Просить знижку"})),
            text_reply("Передав адміністратору."),
            tool_call(("create_booking", {"service_id": "beard", "master_id": "any", "date": "2026-10-27",
                                          "time": "10:00"})),
            text_reply("Натисніть «Підтвердити»."),
        ])
        code, out = self.run_cli(cli.cmd_eval, [], llm=llm, scenarios_path=scenarios)
        self.assertEqual(code, 0, out)
        self.assertIn("2 з 2", out)
        self.assertIn("ПІДТВЕРДЖЕНО (запис №1)", out)
        self.assertTrue((self.tmp / "data" / "eval-shop.txt").exists())


if __name__ == "__main__":
    unittest.main()
