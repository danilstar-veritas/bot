"""Web Push для адмінки на телефоні — на чистому Python.

Push надсилаємо БЕЗ вмісту: так не потрібне шифрування повідомлення (AES-GCM, якого немає в стандартній
бібліотеці). Service worker адмінки, отримавши push, сам забирає текст сповіщення з API (/api/notes).
Залишається лише підпис VAPID (RFC 8292) — ECDSA P-256 + SHA-256 з детермінованим k (RFC 6979).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse

# Крива P-256 (secp256r1)
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = P - 3
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
     0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


def _add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    (x1, y1), (x2, y2) = p1, p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1 + A) * pow(2 * y1, -1, P) % P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    return x3, (lam * (x1 - x3) - y1) % P


def _mul(k: int, point=G):
    result = None
    while k:
        if k & 1:
            result = _add(result, point)
        point = _add(point, point)
        k >>= 1
    return result


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def public_key(private: int) -> bytes:
    """Відкритий ключ у форматі «0x04 || X || Y» (65 байтів) — так його чекає браузер (applicationServerKey)."""
    x, y = _mul(private)
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def new_private_key() -> int:
    return secrets.randbelow(N - 1) + 1


def _rfc6979_k(private: int, digest: bytes) -> int:
    x = private.to_bytes(32, "big")
    h = (int.from_bytes(digest, "big") % N).to_bytes(32, "big")
    v, k = b"\x01" * 32, b"\x00" * 32
    k = hmac.new(k, v + b"\x00" + x + h, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b"\x01" + x + h, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        candidate = int.from_bytes(v, "big")
        if 1 <= candidate < N:
            return candidate
        k = hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def sign(private: int, message: bytes) -> bytes:
    """ECDSA P-256 / SHA-256: r || s (64 байти), як у JWS ES256."""
    digest = hashlib.sha256(message).digest()
    e = int.from_bytes(digest, "big")
    k = _rfc6979_k(private, digest)
    r = _mul(k)[0] % N
    s = pow(k, -1, N) * (e + r * private) % N
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    x, y = int.from_bytes(public[1:33], "big"), int.from_bytes(public[33:], "big")
    r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    if not (1 <= r < N and 1 <= s < N):
        return False
    e = int.from_bytes(hashlib.sha256(message).digest(), "big")
    w = pow(s, -1, N)
    point = _add(_mul(e * w % N), _mul(r * w % N, (x, y)))
    return point is not None and point[0] % N == r


def vapid_headers(private: int, endpoint: str, subject: str, ttl: int = 86400) -> dict[str, str]:
    """Заголовки запиту до push-сервісу браузера (FCM, Apple, Mozilla) для push без вмісту."""
    parts = urllib.parse.urlsplit(endpoint)
    claims = {"aud": f"{parts.scheme}://{parts.netloc}", "exp": int(time.time()) + 12 * 3600, "sub": subject}
    head = b64url(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64url(json.dumps(claims, separators=(",", ":")).encode())
    token = f"{head}.{body}"
    jwt = f"{token}.{b64url(sign(private, token.encode('ascii')))}"
    return {"Authorization": f"vapid t={jwt}, k={b64url(public_key(private))}", "TTL": str(ttl),
            "Urgency": "high", "Content-Length": "0"}
