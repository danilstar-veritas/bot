"""Пул з'єднань (keep-alive): повторне використання, перепідключення, помилки."""

from __future__ import annotations

import json
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from barberbot.llm import LLMError, post_json
from barberbot.telegram import POOL, HttpPool, NetworkError, TelegramAPI, TelegramError


class KeepAliveServer:
    """HTTP/1.1-сервер, що тримає з'єднання відкритими і рахує їх."""

    def __init__(self):
        self.connections = 0
        self.requests = 0
        self.sockets: list[socket.socket] = []
        self.reply = (200, {"ok": True, "result": {"pong": True}})
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def setup(self):
                super().setup()
                server.connections += 1
                server.sockets.append(self.connection)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                server.requests += 1
                status, payload = server.reply
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def drop_connections(self) -> None:
        """Як сервер, що закрив неактивні з'єднання."""
        for s in self.sockets:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


class HttpPoolTests(unittest.TestCase):
    def setUp(self):
        self.srv = KeepAliveServer()
        self.pool = HttpPool()

    def tearDown(self):
        self.pool.close_all()
        POOL.close_all()
        self.srv.close()

    def post(self):
        return self.pool.post(self.srv.base + "/x", b"{}", {"Content-Type": "application/json"}, 5)

    def test_reuses_one_connection(self):
        for _ in range(5):
            status, data, _ = self.post()
            self.assertEqual((status, json.loads(data)["ok"]), (200, True))
        self.assertEqual((self.srv.requests, self.srv.connections), (5, 1))

    def test_reconnects_when_server_closed_idle_connection(self):
        self.post()
        self.srv.drop_connections()
        status, _, _ = self.post()
        self.assertEqual(status, 200)
        self.assertEqual((self.srv.requests, self.srv.connections), (2, 2))

    def test_telegram_api_errors(self):
        api = TelegramAPI("1:x", self.srv.base)
        self.assertEqual(api.call_sync("getMe"), {"pong": True})
        self.srv.reply = (400, {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"})
        with self.assertRaises(TelegramError) as cm:
            api.call_sync("sendMessage", {"chat_id": 1})
        self.assertEqual((cm.exception.code, cm.exception.description), (400, "Bad Request: chat not found"))
        self.assertEqual(self.srv.connections, 1)  # помилка 400 не рве з'єднання

    def test_network_error(self):
        port = self.srv.httpd.server_address[1]
        self.srv.close()
        with self.assertRaises(NetworkError):
            TelegramAPI("1:x", f"http://127.0.0.1:{port}").call_sync("getMe", timeout=2)
        self.srv = KeepAliveServer()  # для tearDown

    def test_llm_http_error_message(self):
        self.srv.reply = (401, {"type": "error", "error": {"message": "invalid x-api-key"}})
        with self.assertRaises(LLMError) as cm:
            post_json(self.srv.base + "/v1/messages", {}, {}, 5, retries=0)
        self.assertEqual((str(cm.exception), cm.exception.status), ("HTTP 401: invalid x-api-key", 401))


if __name__ == "__main__":
    unittest.main()
