"""Мінімальний клієнт Telegram Bot API на стандартній бібліотеці Python."""

from __future__ import annotations

import asyncio
import http.client
import json
import logging
import socket
import ssl
import threading
import time
import urllib.parse

log = logging.getLogger("barberbot.telegram")


def run_blocking(fn, *args) -> asyncio.Future:
    """Виконує блокуючий HTTP-запит в окремому фоновому потоці.

    Потоки «демонічні», тому Ctrl+C зупиняє бота одразу, не чекаючи long polling.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def finish(setter, value):
        if not future.done():
            setter(value)

    def worker():
        try:
            result = fn(*args)
        except BaseException as exc:  # noqa: BLE001 — передаємо будь-яку помилку в asyncio
            try:
                loop.call_soon_threadsafe(finish, future.set_exception, exc)
            except RuntimeError:
                pass
        else:
            try:
                loop.call_soon_threadsafe(finish, future.set_result, result)
            except RuntimeError:
                pass

    threading.Thread(target=worker, daemon=True, name="http").start()
    return future

SSL_HINT = (
    "Не вдається перевірити SSL-сертифікат. На Mac з Python від python.org відкрийте "
    "Програми → Python 3.x → двічі клацніть «Install Certificates.command», потім запустіть бота знову."
)


def make_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore  # необов'язково: якщо встановлено — використовуємо

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()


def create_ipv4_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    """Як socket.create_connection, але лише через IPv4.

    Python (http.client), на відміну від браузера, не пробує IPv4 та IPv6 паралельно: якщо IPv6 «зависає»,
    кожен запит чекає повний таймаут (30 с), і лише потім пробує IPv4.
    Якщо в адреси немає IPv4 — звичайне підключення.
    """
    host, port = address
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except socket.gaierror:
        return socket.create_connection(address, timeout, source_address)
    error = None
    for family, type_, proto, _, sockaddr in infos:
        sock = socket.socket(family, type_, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            error = e
            sock.close()
    raise error


class IPv4HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = create_ipv4_connection


# Помилки мережі, які може кинути http.client (таймаути, обриви, SSL — це OSError).
NET_ERRORS = (OSError, http.client.HTTPException)


class HttpPool:
    """POST-запити з повторним використанням з'єднань (keep-alive).

    Нове з'єднання — це TCP + TLS: із сервера до Telegram ~320 мс на запит, а на вже відкритому — ~105 мс.
    Запити йдуть із різних потоків (run_blocking), тому вільні з'єднання лежать у спільному списку під замком;
    одне з'єднання одночасно використовує лише один потік.
    """

    MAX_IDLE = 8          # скільки вільних з'єднань тримати на один сервер
    IDLE_SECONDS = 50     # старіші не використовуємо: сервер міг їх уже закрити

    def __init__(self):
        self._idle: dict[tuple[str, str, int], list[tuple[http.client.HTTPConnection, float]]] = {}
        self._lock = threading.Lock()

    def _take(self, key: tuple[str, str, int]) -> http.client.HTTPConnection | None:
        now = time.monotonic()
        with self._lock:
            idle = self._idle.get(key, [])
            while idle:
                conn, used = idle.pop()
                if now - used < self.IDLE_SECONDS:
                    return conn
                conn.close()
        return None

    def _give(self, key: tuple[str, str, int], conn: http.client.HTTPConnection) -> None:
        with self._lock:
            idle = self._idle.setdefault(key, [])
            if len(idle) < self.MAX_IDLE:
                idle.append((conn, time.monotonic()))
                return
        conn.close()

    def close_all(self) -> None:
        """Закрити всі вільні з'єднання."""
        with self._lock:
            idle, self._idle = self._idle, {}
        for conns in idle.values():
            for conn, _ in conns:
                conn.close()

    def post(self, url: str, body: bytes, headers: dict, timeout: float) -> tuple[int, bytes, http.client.HTTPMessage]:
        """Повертає (статус, тіло, заголовки). Помилки мережі — винятки з NET_ERRORS."""
        parts = urllib.parse.urlsplit(url)
        https = parts.scheme == "https"
        key = (parts.scheme, parts.hostname or "", parts.port or (443 if https else 80))
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        headers = {"User-Agent": "barberbot", **headers}
        while True:
            conn = self._take(key)
            reused = conn is not None
            if conn is None:
                conn = IPv4HTTPSConnection(key[1], key[2], timeout=timeout, context=SSL_CONTEXT) if https \
                    else http.client.HTTPConnection(key[1], key[2], timeout=timeout)
            conn.timeout = timeout
            if conn.sock is not None:
                conn.sock.settimeout(timeout)
            try:
                conn.request("POST", path, body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
            except (ConnectionResetError, BrokenPipeError, http.client.RemoteDisconnected,
                    http.client.CannotSendRequest):
                conn.close()
                if reused:
                    continue  # сервер уже закрив старе з'єднання й запит не отримав — пробуємо на новому
                raise
            except BaseException:
                conn.close()
                raise
            if resp.will_close:
                conn.close()
            else:
                self._give(key, conn)
            return resp.status, data, resp.headers


POOL = HttpPool()


class TelegramError(Exception):
    def __init__(self, code: int, description: str, retry_after: int | None = None):
        super().__init__(f"{code}: {description}")
        self.code = code
        self.description = description
        self.retry_after = retry_after

    @property
    def not_modified(self) -> bool:
        return "message is not modified" in self.description

    @property
    def blocked(self) -> bool:
        return self.code == 403


class NetworkError(Exception):
    pass


def is_ssl_error(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)


class TelegramAPI:
    def __init__(self, token: str, base_url: str = "https://api.telegram.org"):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def call_sync(self, method: str, params: dict | None = None, timeout: float = 30) -> object:
        url = f"{self.base_url}/bot{self.token}/{method}"
        data = json.dumps(params or {}, ensure_ascii=False).encode("utf-8")
        try:
            status, raw, _ = POOL.post(url, data, {"Content-Type": "application/json"}, timeout)
        except NET_ERRORS as e:
            if is_ssl_error(e):
                raise NetworkError(SSL_HINT) from None
            raise NetworkError(str(e) or e.__class__.__name__) from None
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise TelegramError(status, http.client.responses.get(status, f"HTTP {status}")) from None
        if not body.get("ok"):
            params_ = body.get("parameters") or {}
            raise TelegramError(int(body.get("error_code") or 0), str(body.get("description") or ""),
                                params_.get("retry_after"))
        return body.get("result")

    async def call(self, method: str, _timeout: float = 30, _retries: int = 2, **params) -> object:
        """Асинхронний виклик методу Bot API з повторами при збоях мережі та 429."""
        params = {k: v for k, v in params.items() if v is not None}
        attempt = 0
        while True:
            try:
                return await run_blocking(self.call_sync, method, params, _timeout)
            except TelegramError as e:
                if e.code == 429 and attempt < _retries:
                    await asyncio.sleep(min(float(e.retry_after or 1), 30))
                    attempt += 1
                    continue
                raise
            except NetworkError:
                if attempt < _retries:
                    await asyncio.sleep(1 + attempt * 2)
                    attempt += 1
                    continue
                raise


# ------------------------------------------------------------------ keyboards

def ibtn(text: str, data: str) -> dict:
    if len(data.encode("utf-8")) > 64:
        raise ValueError(f"callback_data задовгий: {data}")
    return {"text": text, "callback_data": data}


def url_btn(text: str, url: str) -> dict:
    return {"text": text, "url": url}


def inline_kb(rows: list[list[dict]]) -> dict:
    return {"inline_keyboard": [row for row in rows if row]}


def reply_kb(rows: list[list[str | dict]], one_time: bool = False) -> dict:
    keyboard = [[b if isinstance(b, dict) else {"text": b} for b in row] for row in rows if row]
    return {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": not one_time,
            "one_time_keyboard": one_time}


def chunk_text(text: str, limit: int = 3800) -> list[str]:
    """Ділить довгий текст на частини по рядках (ліміт Telegram — 4096 символів)."""
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts
