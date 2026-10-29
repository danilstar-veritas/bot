"""Адмінка на телефоні (PWA) для власника й майстрів, вхід для Siri / Google і MCP-сервер для ChatGPT / Claude.

Маршрути (назовні — HTTPS через Caddy, як і онлайн-запис):
/staff/<заклад>/                  застосунок: barberbot/staff_web/index.html, manifest, service worker, іконки
/staff/<заклад>/login?t=<код>     одноразовий вхід за посиланням із бота (/app) → cookie сесії на 60 днів
/staff/<заклад>/api/<дія>         JSON API: зі сторінки (cookie) або від Siri (Authorization: Bearer <ключ>)

Голос розпізнає сам телефон: у застосунку — розпізнавання мови браузера (Siri / Google), у Siri — «Диктувати
текст», у ChatGPT / Claude — їхній голосовий режим. Сюди завжди приходить уже текст.
/mcp/<заклад>/<ключ>              MCP-сервер (mcp.py) для конектора в ChatGPT / Claude / Gemini

Хто ця людина — завжди її чат (Telegram ID чи чат Messenger), яким вона підключена до закладу як власник
(admins) або майстер. Права й дії — ті самі, що в боті (staff.py).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import secrets
import struct
import urllib.parse
import zlib
from datetime import datetime, timedelta
from pathlib import Path

from . import webpush
from .mcp import McpServer
from .staff import StaffError, staff_user
from .telegram import NET_ERRORS, POOL, run_blocking
from .util import short
from .web import Response

log = logging.getLogger("barberbot.staff_web")

STATIC = Path(__file__).with_name("staff_web")
PATH_RE = re.compile(r"^/staff/([A-Za-z0-9_-]{1,40})/(.*)$")
MCP_RE = re.compile(r"^/mcp/([A-Za-z0-9_-]{1,40})/([A-Za-z0-9_-]{20,80})$")
LOGIN_TTL = timedelta(minutes=15)
SESSION_DAYS = 60
NOTES_KEEP = 30


def json_response(data, status: int = 200, headers: dict | None = None) -> Response:
    return Response(status, json.dumps(data, ensure_ascii=False, default=str), "application/json; charset=utf-8",
                    {"Cache-Control": "no-store", **(headers or {})})


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- іконка застосунку (PNG без бібліотек)

def icon_png(size: int) -> bytes:
    """Ножиці на темному тлі. Малюємо попіксельно з плавними краями й пакуємо в PNG (zlib + struct)."""
    bg, gold = (24, 22, 20), (214, 170, 92)
    s = size / 512

    def seg_dist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5

    rings = [(176 * s, 352 * s), (336 * s, 352 * s)]
    blades = [((206 * s, 318 * s), (372 * s, 120 * s)), ((306 * s, 318 * s), (140 * s, 120 * s))]
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            ink = 0.0
            for cx, cy in rings:
                d = abs(((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 - 46 * s)
                ink = max(ink, min(1.0, max(0.0, 15 * s - d + 0.5)))
            for (ax, ay), (bx, by) in blades:
                d = seg_dist(px, py, ax, ay, bx, by)
                ink = max(ink, min(1.0, max(0.0, 17 * s - d + 0.5)))
            d = ((px - 256 * s) ** 2 + (py - 262 * s) ** 2) ** 0.5
            ink = max(ink, min(1.0, max(0.0, 13 * s - d + 0.5)))
            rows.extend(round(b + (g - b) * ink) for b, g in zip(bg, gold))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) \
        + chunk(b"IEND", b"")


class StaffWeb:
    def __init__(self, app):
        self.app = app
        self.db = app.db
        self.settings = app.settings
        self.mcp = McpServer(app)
        self.icons: dict[int, bytes] = {}
        raw = self.db.kv_get("_web", "vapid_private")
        if not raw:
            raw = str(webpush.new_private_key())
            self.db.kv_set("_web", "vapid_private", raw)
        self.vapid_private = int(raw)
        self.vapid_public = webpush.b64url(webpush.public_key(self.vapid_private))

    # ================================================================ посилання й вхід
    def base(self, tenant) -> str:
        return f"{self.settings.web_base_url}/staff/{tenant.slug}/"

    def login_url(self, tenant, chat_id: int) -> str:
        code = secrets.token_urlsafe(24)
        until = tenant.now() + LOGIN_TTL
        self.db.kv_set(tenant.slug, f"staff_login:{code}", json.dumps({"chat": chat_id, "until": until.isoformat()}))
        return f"{self.base(tenant)}login?t={code}"

    def _login(self, tenant, code: str) -> Response:
        key = f"staff_login:{code}"
        raw = self.db.kv_get(tenant.slug, key) if code else None
        if raw:
            self.db.kv_delete(tenant.slug, key)  # посилання одноразове
        try:
            item = json.loads(raw) if raw else None
            if item and datetime.fromisoformat(item["until"]) < tenant.now():
                item = None
        except (ValueError, KeyError):
            item = None
        if not item or staff_user(self.app, tenant, int(item["chat"])) is None:
            return Response(403, LOGIN_FAILED, "text/html; charset=utf-8")
        sid = secrets.token_urlsafe(32)
        until = tenant.now() + timedelta(days=SESSION_DAYS)
        self.db.kv_set(tenant.slug, f"staff_session:{_hash(sid)}",
                       json.dumps({"chat": item["chat"], "until": until.isoformat()}))
        cookie = (f"bb_staff={sid}; Path=/staff/{tenant.slug}/; Max-Age={SESSION_DAYS * 86400}; HttpOnly; Secure; "
                  f"SameSite=Lax")
        return Response(303, "", headers={"Location": self.base(tenant), "Set-Cookie": cookie})

    @staticmethod
    def _sid(headers: dict[str, str]) -> str:
        cookies = dict(p.strip().split("=", 1) for p in headers.get("cookie", "").split(";") if "=" in p)
        return cookies.get("bb_staff", "")

    def _session_chat(self, tenant, headers: dict[str, str]) -> int | None:
        sid = self._sid(headers)
        raw = self.db.kv_get(tenant.slug, f"staff_session:{_hash(sid)}") if sid else None
        try:
            item = json.loads(raw) if raw else None
            if item and datetime.fromisoformat(item["until"]) >= tenant.now():
                return int(item["chat"])
        except (ValueError, KeyError):
            pass
        return None

    def _key_chat(self, tenant, key: str) -> int | None:
        raw = self.db.kv_get(tenant.slug, f"staff_key:{_hash(key)}") if key else None
        try:
            return int(json.loads(raw)["chat"]) if raw else None
        except (ValueError, KeyError):
            return None

    def new_key(self, u) -> str:
        """Особистий ключ для Siri і MCP. Новий ключ скасовує попередній."""
        tenant = u.tenant
        old = self.db.kv_get(tenant.slug, f"staff_keyof:{u.chat_id}")
        if old:
            self.db.kv_delete(tenant.slug, f"staff_key:{old}")
        key = secrets.token_urlsafe(30)
        self.db.kv_set(tenant.slug, f"staff_key:{_hash(key)}",
                       json.dumps({"chat": u.chat_id, "created": tenant.now().isoformat()}))
        self.db.kv_set(tenant.slug, f"staff_keyof:{u.chat_id}", _hash(key))
        return key

    # ================================================================ маршрути
    async def handle(self, method: str, target: str, headers: dict[str, str], body: bytes) -> Response:
        parts = urllib.parse.urlsplit(target)
        m = MCP_RE.match(parts.path)
        if m:
            return await self._mcp(m.group(1), m.group(2), method, headers, body)
        m = PATH_RE.match(parts.path)
        if not m:
            if re.fullmatch(r"/staff/[A-Za-z0-9_-]{1,40}", parts.path):
                return Response(301, "", headers={"Location": parts.path + "/"})
            return Response(404, "not found")
        tenant = self.app.tenants.get(m.group(1))
        if tenant is None:
            return Response(404, "not found")
        rest = m.group(2)
        query = dict(urllib.parse.parse_qsl(parts.query))
        if rest in ("", "index.html") and method == "GET":
            return Response(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8",
                            {"Cache-Control": "no-cache"})
        if rest == "sw.js" and method == "GET":
            return Response(200, (STATIC / "sw.js").read_bytes(), "text/javascript; charset=utf-8",
                            {"Cache-Control": "no-cache"})
        if rest == "manifest.webmanifest" and method == "GET":
            return Response(200, json.dumps(self.manifest(tenant), ensure_ascii=False),
                            "application/manifest+json; charset=utf-8", {"Cache-Control": "no-cache"})
        icon = re.fullmatch(r"icon-(192|512)\.png", rest)
        if icon and method == "GET":
            size = int(icon.group(1))
            if size not in self.icons:
                self.icons[size] = await run_blocking(icon_png, size)
            return Response(200, self.icons[size], "image/png", {"Cache-Control": "public, max-age=604800"})
        if rest == "login" and method == "GET":
            return self._login(tenant, query.get("t", ""))
        if rest.startswith("api/"):
            return await self.api(tenant, method, rest[4:], query, headers, body)
        return Response(404, "not found")

    def manifest(self, tenant) -> dict:
        base = f"/staff/{tenant.slug}/"
        return {"name": f"{tenant.name} · Admin", "short_name": short(tenant.name, 12), "start_url": base,
                "scope": base, "id": base, "display": "standalone", "background_color": "#181614",
                "theme_color": "#181614", "lang": tenant.lang,
                "icons": [{"src": f"{base}icon-192.png", "sizes": "192x192", "type": "image/png"},
                          {"src": f"{base}icon-512.png", "sizes": "512x512", "type": "image/png",
                           "purpose": "any maskable"}],
                "shortcuts": [{"name": "🎙", "url": f"{base}#voice"}]}

    async def _mcp(self, slug: str, key: str, method: str, headers: dict[str, str], body: bytes) -> Response:
        tenant = self.app.tenants.get(slug)
        chat = self._key_chat(tenant, key) if tenant else None
        u = staff_user(self.app, tenant, chat) if chat is not None else None
        if u is None:
            # 404, а не 401: на 401 клієнти MCP (claude.ai, ChatGPT) вирішують, що потрібен вхід OAuth,
            # і запам'ятовують це для всього сервера. Ключа в адресі немає чи його перевипущено — адреси просто немає.
            response = json_response({"jsonrpc": "2.0", "id": None,
                                      "error": {"code": -32001, "message": "Unknown connector URL"}}, 404)
        else:
            async with self.app.locks[(tenant.slug, u.chat_id)]:
                status, data = await self.mcp.handle(u, method, body)
            response = json_response(data, status) if data is not None else Response(status, "")
        try:
            rpc = json.loads(body.decode("utf-8") or "{}").get("method", "") if method == "POST" else ""
        except (ValueError, AttributeError, UnicodeDecodeError):
            rpc = "?"
        log.info("MCP %s %s %s → %s (%s)", slug, method, rpc, response.status,
                 short(headers.get("user-agent", ""), 60))  # ключ з адреси не пишемо
        return response

    # ================================================================ API
    async def api(self, tenant, method: str, action: str, query: dict, headers: dict[str, str],
                  body: bytes) -> Response:
        auth = headers.get("authorization", "")
        by_key = auth.lower().startswith("bearer ")
        chat = self._key_chat(tenant, auth[7:].strip()) if by_key else self._session_chat(tenant, headers)
        if by_key and action != "ask":
            return json_response({"error": "forbidden"}, 403)  # ключ Siri — лише для запитань помічнику
        if not by_key and method == "POST" and headers.get("x-requested-with") != "staff":
            return json_response({"error": "forbidden"}, 403)  # захист від підроблених форм з інших сайтів
        u = staff_user(self.app, tenant, chat) if chat is not None else None
        if u is None:
            return json_response({"error": "unauthorized"}, 401)
        if action == "logout" and method == "POST" and not by_key:
            self.db.kv_delete(tenant.slug, f"staff_session:{_hash(self._sid(headers))}")
            return json_response({"ok": True}, headers={
                "Set-Cookie": f"bb_staff=; Path=/staff/{tenant.slug}/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"})
        try:
            data = json.loads(body.decode("utf-8") or "{}") if method == "POST" else {}
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return json_response({"error": "bad_request"}, 400)
        try:
            async with self.app.locks[(tenant.slug, u.chat_id)]:
                result = await self.dispatch(u, method, action, query, data)
        except StaffError as e:
            return json_response({"error": e.code, "message": e.message}, 400)
        if result is None:
            return json_response({"error": "not_found"}, 404)
        if by_key and query.get("format") == "text":
            return Response(200, result.get("text", ""), "text/plain; charset=utf-8", {"Cache-Control": "no-store"})
        return json_response(result)

    async def dispatch(self, u, method: str, action: str, q: dict, d: dict) -> dict | None:
        ops, staff, tenant = self.app.staff.ops, self.app.staff, u.tenant
        if method == "GET":
            if action == "me":
                return self.me(u)
            if action == "day":
                return ops.schedule(u, q.get("date"), 1, q.get("master"))
            if action == "week":
                return ops.schedule(u, q.get("date"), 7, q.get("master"))
            if action == "slots":
                return ops.free_slots(u, q.get("service", ""), q.get("date"), q.get("master"))
            if action == "clients":
                return ops.find_clients(u, q.get("q", ""))
            if action == "report":
                return ops.report(u, q.get("period", "today"))
            if action == "blocks":
                return ops.blocks(u)
            if action == "chats":
                return ops.chats(u)
            if action == "notes":
                return {"notes": self.notes(u)}
            return None
        if action == "propose":
            return ops.propose(u, str(d.get("kind") or ""), d)
        if action == "confirm":
            return self._reply(await staff.confirm(u, str(d.get("action_id") or "")))
        if action == "decline":
            ops.drop(u, str(d.get("action_id") or ""))
            return {"ok": True, "text": short(tenant.t(tenant.lang, "staff_declined"), 200)}
        if action == "ask":
            text = str(d.get("text") or "").strip()
            return self._reply(await staff.ask(u, text)) if text else {"text": ""}
        if action == "resume":
            ops.resume_ai(u, d.get("client_id"))
            return {"ok": True}
        if action == "push":
            return self.subscribe(u, d)
        if action == "key":
            key = self.new_key(u)
            return {"key": key, "ask_url": f"{self.base(tenant)}api/ask",
                    "mcp_url": f"{self.settings.web_base_url}/mcp/{tenant.slug}/{key}"}
        return None

    def _reply(self, reply) -> dict:
        return {"text": reply.text, "action": reply.action, "done": reply.done, "error": reply.error}

    def me(self, u) -> dict:
        tenant = u.tenant
        return {
            "shop": tenant.name, "lang": tenant.lang, "role": u.role, "name": u.name(self.db), "master_id": u.master_id,
            "today": tenant.today().isoformat(), "now": tenant.now().strftime("%H:%M"),
            "masters": [{"id": m.id, "name": m.name, "services": m.services} for m in tenant.masters.values()],
            "services": [{"id": s.id, "title": s.title, "duration": s.duration, "price": tenant.price_str(s.price)}
                         for s in tenant.services.values() if not (s.hidden and not s.base_id)],
            "ai": self.app.staff.agent is not None,
            "push_key": self.vapid_public, "pending": self.app.staff.ops.pending_view(u),
        }

    # ================================================================ сповіщення (стрічка + Web Push)
    def notes(self, u) -> list[dict]:
        return self._notes_raw(u.tenant, u.chat_id)

    def subscribe(self, u, d: dict) -> dict:
        endpoint = str(d.get("endpoint") or "")
        if not endpoint.startswith("https://"):
            raise StaffError("bad_input", "bad endpoint")
        key = f"push_sub:{u.chat_id}:{_hash(endpoint)[:16]}"
        if d.get("remove"):
            self.db.kv_delete(u.tenant.slug, key)
        else:
            self.db.kv_set(u.tenant.slug, key, json.dumps({"endpoint": endpoint, "at": u.tenant.now().isoformat()}))
        return {"ok": True}

    def notify(self, tenant, chats, text: str) -> None:
        """Сповіщення персоналу (нові записи, скасування…) — ще й у стрічку адмінки та Web Push на телефони."""
        from .staff import strip_tags

        plain = strip_tags(text).strip()
        title, _, rest = plain.partition("\n")
        for chat in {c for c in chats if c}:
            notes = self._notes_raw(tenant, chat)[-(NOTES_KEEP - 1):]
            notes.append({"id": secrets.token_hex(4), "at": tenant.now().strftime("%Y-%m-%d %H:%M"),
                          "title": short(title, 120), "body": short(rest.strip(), 400)})
            self.db.kv_set(tenant.slug, f"staff_notes:{chat}", json.dumps(notes, ensure_ascii=False))
            subs = self.db.kv_prefix(tenant.slug, f"push_sub:{chat}:")
            if subs:
                self.app.spawn(self._push_all(tenant, subs))

    def _notes_raw(self, tenant, chat: int) -> list[dict]:
        raw = self.db.kv_get(tenant.slug, f"staff_notes:{chat}")
        try:
            return json.loads(raw) if raw else []
        except ValueError:
            return []

    async def _push_all(self, tenant, subs: dict[str, str]) -> None:
        for key, raw in subs.items():
            try:
                endpoint = json.loads(raw)["endpoint"]
            except (ValueError, KeyError):
                self.db.kv_delete(tenant.slug, key)
                continue
            headers = webpush.vapid_headers(self.vapid_private, endpoint, self.settings.web_base_url)
            try:
                status, _, _ = await run_blocking(POOL.request, "POST", endpoint, b"", headers, 15)
            except NET_ERRORS as e:
                log.info("[%s] Web Push: %s", tenant.name, e)
                continue
            if status in (404, 410):  # підписку скасовано в браузері
                self.db.kv_delete(tenant.slug, key)
            elif status >= 400:
                log.info("[%s] Web Push: HTTP %s", tenant.name, status)
            await asyncio.sleep(0)


LOGIN_FAILED = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin</title><body style="font:17px system-ui;background:#181614;color:#f3eee7;padding:32px;text-align:center">
<p style="font-size:44px;margin:24px 0 8px">🔒</p>
<p>Посилання недійсне або вже використане.<br>Напишіть боту <b>/app</b>, щоб отримати нове.</p>
<p style="opacity:.7">The link is invalid or used. Send <b>/app</b> to the bot for a new one.<br>
A link érvénytelen. Írja be a botnak: <b>/app</b>.</p></body>"""
