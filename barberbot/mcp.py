"""MCP-сервер: власник чи майстер підключає заклад до свого ChatGPT, Claude або Gemini як конектор
і далі просто питає свій AI: «що в мене завтра?», «закрий пʼятницю після 15:00».

Транспорт — Streamable HTTP (https://modelcontextprotocol.io/specification/2025-06-18/basic/transports):
POST з JSON-RPC 2.0, відповідь — один JSON. Адреса містить особистий ключ людини
(<base_url>/mcp/<заклад>/<ключ>) — так конектор працює без окремого входу, а ключ можна будь-коли
перевипустити в адмінці. Інструменти ті самі, що в помічника персоналу (staff.py), і з тими самими правами:
усе нове, що додається в staff_tools(), зʼявляється тут само. Плюс ask_bot_assistant — розмова з AI самого бота.
Зміни двокрокові: інструмент готує дію, а confirm_action виконує її — лише після явного «так» людини.
"""

from __future__ import annotations

import json
import logging

from .staff import StaffTools, staff_tools

log = logging.getLogger("barberbot.mcp")

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = (
    "Full admin access to a barbershop's booking bot on behalf of its owner (or a master, with fewer rights). "
    "Read: schedule, free slots, clients, client chats, reports and stats, shop status (prices, client AI, masters). "
    "Change: block/unblock time, book, reschedule, cancel, no-show, message a client, set prices, turn the client AI "
    "on/off, hand a client back to the AI, invite a master, send an Excel export. Use the specific tools first; for "
    "anything they don't cover, or to talk to the bot's own AI, use ask_bot_assistant. "
    "Every change tool only PREPARES the action and returns action_id and a summary. Show the summary to the user "
    "and call confirm_action(action_id) only after the user explicitly agrees. Dates are YYYY-MM-DD, times HH:MM, "
    "in the shop's local time. Answer in the user's language.")
EXTRA_TOOLS = [
    {"name": "ask_bot_assistant",
     "description": "Say something to the bot's own staff AI in plain words, as the owner would in the bot chat, and "
                    "get its answer. If it prepares a change, the result has action_id + summary: confirm the same "
                    "way, with confirm_action after the user agrees.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "confirm_action",
     "description": "Execute a prepared change. Call ONLY after the user explicitly confirmed this exact summary.",
     "inputSchema": {"type": "object", "properties": {"action_id": {"type": "string"}}, "required": ["action_id"]}},
    {"name": "cancel_action", "description": "Discard a prepared change the user declined.",
     "inputSchema": {"type": "object", "properties": {"action_id": {"type": "string"}}, "required": ["action_id"]}},
]


def tool_list() -> list[dict]:
    return [{"name": t["name"], "description": t["description"], "inputSchema": t["input_schema"]}
            for t in staff_tools()] + EXTRA_TOOLS


class McpServer:
    def __init__(self, app):
        self.app = app

    @staticmethod
    def _ok(req_id, result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _fail(req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    async def call(self, u, request: dict) -> dict | None:
        """Один запит JSON-RPC → відповідь (None — це було сповіщення, відповідати не треба)."""
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not request.get("method"):
            return self._fail(None, -32600, "Invalid Request")
        method, req_id = request["method"], request.get("id")
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        if req_id is None:
            return None  # notifications/initialized, notifications/cancelled тощо
        if method == "initialize":
            version = params.get("protocolVersion")
            return self._ok(req_id, {
                "protocolVersion": version if version in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "barberbot", "title": u.tenant.name, "version": "1.0"},
                "instructions": INSTRUCTIONS + f" Shop: {u.tenant.name}. You act as the "
                                               f"{'owner' if u.is_owner else 'master ' + u.tenant.masters[u.master_id].name}.",
            })
        if method == "ping":
            return self._ok(req_id, {})
        if method == "tools/list":
            return self._ok(req_id, {"tools": tool_list()})
        if method == "tools/call":
            name = str(params.get("name") or "")
            args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            out = await self.run_tool(u, name, args)
            self.app.db.log_event(u.tenant.slug, u.client_id, "mcp_call", u.tenant.now(), {"tool": name})
            return self._ok(req_id, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                                     "structuredContent": out, "isError": "error" in out})
        return self._fail(req_id, -32601, f"Method not found: {method}")

    async def run_tool(self, u, name: str, args: dict) -> dict:
        staff = self.app.staff
        if name == "confirm_action":
            reply = await staff.confirm(u, str(args.get("action_id") or ""))
            return {"error": reply.error, "message": reply.text} if reply.error else {"ok": True,
                                                                                      "message": reply.text}
        if name == "ask_bot_assistant":
            reply = await staff.ask(u, str(args.get("text") or ""))
            if reply.error:
                return {"error": reply.error, "message": reply.text}
            out = {"reply": reply.text}
            if reply.action:
                out.update(action_id=reply.action["action_id"], summary=reply.action["summary"],
                           note="Not executed yet. Show the summary to the user; call confirm_action only after "
                                "they agree.")
            return out
        if name == "cancel_action":
            staff.ops.drop(u, str(args.get("action_id") or ""))
            return {"ok": True}
        tools = StaffTools(staff.ops, u)
        out = tools.run(name, args)
        if tools.action:
            out["note"] = "Not executed yet. Show the summary to the user; call confirm_action only after they agree."
        return out

    async def handle(self, u, method: str, body: bytes) -> tuple[int, dict | None]:
        if method != "POST":
            return 405, None
        try:
            request = json.loads(body.decode("utf-8") or "null")
        except (ValueError, UnicodeDecodeError):
            return 400, self._fail(None, -32700, "Parse error")
        if isinstance(request, list):
            return 400, self._fail(None, -32600, "Batching is not supported")
        response = await self.call(u, request)
        return (202, None) if response is None else (200, response)
