"""Маленький HTTP-сервер бота на стандартній бібліотеці.

Слухає 127.0.0.1 (порт [web] port / [meta] webhook_port), а назовні його з HTTPS відкриває Caddy.
Маршрути: /meta/webhook — вебхук Instagram/Messenger, /app/<заклад>/… — міні-застосунок запису,
/staff/<заклад>/… — адмінка персоналу (PWA), /mcp/<заклад>/<ключ> — MCP-сервер, /health.
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse

log = logging.getLogger("barberbot.web")

REASONS = {200: "OK", 202: "Accepted", 301: "Moved Permanently", 303: "See Other", 400: "Bad Request",
           401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict",
           413: "Payload Too Large", 429: "Too Many Requests", 500: "Internal Server Error"}


class Response:
    def __init__(self, status: int, body: bytes | str = b"", content_type: str = "text/plain; charset=utf-8",
                 headers: dict[str, str] | None = None):
        self.status = status
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.content_type = content_type
        self.headers = headers or {}


class WebServer:
    MAX_BODY = 1 << 20

    def __init__(self, settings, meta_hook=None, webapp=None, staff_web=None):
        self.meta_hook = meta_hook
        self.webapp = webapp
        self.staff_web = staff_web
        self.host, self.port = settings.meta_webhook_host, settings.meta_webhook_port
        self.server: asyncio.base_events.Server | None = None

    async def start(self) -> None:
        self.server = await asyncio.start_server(self.on_connection, self.host, self.port)
        parts = [p for p, on in (("вебхук Instagram/Messenger /meta/webhook", self.meta_hook),
                                 ("онлайн-запис /app/", self.webapp),
                                 ("адмінка /staff/ і MCP /mcp/", self.staff_web)) if on]
        log.info("HTTP-сервер слухає %s:%s — %s", self.host, self.port, ", ".join(parts))

    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

    async def route(self, method: str, target: str, headers: dict[str, str], body: bytes) -> Response:
        path = urllib.parse.urlsplit(target).path
        if path == "/health":
            return Response(200, "ok")
        if path.startswith("/meta/") and self.meta_hook:
            status, text = await self.meta_hook.respond(method, target, headers, body)
            return Response(status, text)
        if path.startswith("/app/") and self.webapp:
            return await self.webapp.handle(method, target, headers, body)
        if path.startswith(("/staff/", "/mcp/")) and self.staff_web:
            return await self.staff_web.handle(method, target, headers, body)
        return Response(404, "not found")

    async def on_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        response = Response(400, "bad request")
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 15)
            lines = head.decode("latin-1").split("\r\n")
            method, target, _ = lines[0].split(" ", 2)
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            length = int(headers.get("content-length") or 0)
            if length > self.MAX_BODY:
                response = Response(413, "too large")
            else:
                body = await asyncio.wait_for(reader.readexactly(length), 15) if length else b""
                response = await self.route(method.upper(), target, headers, body)
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError, ValueError):
            pass
        except Exception:
            log.exception("HTTP: помилка обробки запиту")
            response = Response(500, "error")
        extra = "".join(f"{k}: {v}\r\n" for k, v in response.headers.items())
        try:
            writer.write(f"HTTP/1.1 {response.status} {REASONS.get(response.status, 'OK')}\r\n"
                         f"Content-Type: {response.content_type}\r\nContent-Length: {len(response.body)}\r\n"
                         f"{extra}Connection: close\r\n\r\n".encode("latin-1") + response.body)
            await writer.drain()
        except OSError:
            pass
        finally:
            writer.close()
