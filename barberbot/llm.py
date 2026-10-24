"""Клієнти AI на стандартній бібліотеці: Claude Messages API (https://platform.claude.com/docs)
і Gemini API (https://ai.google.dev/gemini-api/docs).

Агент завжди працює у форматі Claude Messages API. GeminiClient перекладає цей формат
у запит Gemini, а відповідь Gemini — назад у формат Claude, тож решта бота не знає,
яка модель відповідає.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from collections import OrderedDict

from .telegram import HTTPS_OPENER, SSL_HINT, is_ssl_error, run_blocking

log = logging.getLogger("barberbot.llm")

API_VERSION = "2023-06-01"
RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504, 529}


class LLMError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def post_json(url: str, payload: dict, headers: dict, timeout: float, retries: int) -> dict:
    """POST JSON з повторами при збоях мережі, 429 і 5xx."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={**headers, "content-type": "application/json"},
    )
    attempt = 0
    while True:
        try:
            with HTTPS_OPENER.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
                message = body.get("error", {}).get("message") or str(body)
            except Exception:
                message = str(e.reason)
            if e.code in RETRY_STATUSES and attempt < retries:
                retry_after = e.headers.get("retry-after") if e.headers else None
                try:
                    delay = min(float(retry_after), 20) if retry_after else 1.5 * (attempt + 1)
                except ValueError:
                    delay = 1.5 * (attempt + 1)
                time.sleep(delay)
                attempt += 1
                continue
            raise LLMError(f"HTTP {e.code}: {message}", e.code) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if is_ssl_error(e):
                raise LLMError(SSL_HINT) from None
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                attempt += 1
                continue
            raise LLMError(f"Мережа: {e}") from None


class ClaudeClient:
    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com", timeout: float = 90,
                 retries: int = 2):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    def _post(self, path: str, payload: dict) -> dict:
        headers = {"x-api-key": self.api_key, "anthropic-version": API_VERSION}
        return post_json(f"{self.base_url}{path}", payload, headers, self.timeout, self.retries)

    def create_sync(self, payload: dict) -> dict:
        return self._post("/v1/messages", payload)

    async def create(self, payload: dict) -> dict:
        return await run_blocking(self.create_sync, payload)

    def count_tokens_sync(self, payload: dict) -> int:
        """Безкоштовна перевірка ключа і підрахунок токенів."""
        result = self._post("/v1/messages/count_tokens", payload)
        return int(result.get("input_tokens", 0))


# ------------------------------------------------------------------ Gemini

# Gemini 3+ вимагає повертати thoughtSignature разом із викликом інструмента в межах поточного ходу.
# Для старіших ходів (наприклад, після перезапуску бота) Google дозволяє підставити цю заглушку.
DUMMY_SIGNATURE = "skip_thought_signature_validator"
GENERATED_ID_PREFIX = "gmn_"  # id, які ми придумали самі (стара модель не дала свого) — у Gemini не передаємо
REFUSAL_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}
EFFORT_BUDGET = {"low": 1024, "medium": 4096, "high": 8192}


def _text_of(system) -> str:
    if isinstance(system, str):
        return system
    return "\n\n".join(b.get("text", "") for b in system or [] if b.get("type") == "text")


def _blocks(content) -> list[dict]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content else []
    return [b for b in content or [] if isinstance(b, dict)]


def _tool_response(content) -> dict:
    """tool_result у Claude — рядок JSON; Gemini чекає об'єкт."""
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    try:
        value = json.loads(content)
    except (TypeError, ValueError):
        value = content
    return value if isinstance(value, dict) else {"result": value}


class GeminiClient:
    def __init__(self, api_key: str, model: str, base_url: str = "https://generativelanguage.googleapis.com",
                 timeout: float = 90, retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.signatures: OrderedDict[str, str] = OrderedDict()  # id виклику інструмента → thoughtSignature

    def _post(self, method: str, payload: dict) -> dict:
        url = f"{self.base_url}/v1beta/models/{self.model}:{method}"
        return post_json(url, payload, {"x-goog-api-key": self.api_key}, self.timeout, self.retries)

    # ---------------------------------------------------------- Claude → Gemini
    def _thinking_config(self, payload: dict) -> dict | None:
        effort = (payload.get("output_config") or {}).get("effort")
        disabled = (payload.get("thinking") or {}).get("type") == "disabled"
        if self.model.startswith("gemini-2"):
            if disabled:
                return {"thinkingBudget": 0}
            return {"thinkingBudget": EFFORT_BUDGET[effort]} if effort in EFFORT_BUDGET else None
        if effort in EFFORT_BUDGET:
            return {"thinkingLevel": "low" if disabled else effort}
        return None

    def _contents(self, messages: list[dict]) -> list[dict]:
        names: dict[str, str] = {}
        contents = []
        for m in messages:
            parts = []
            for b in _blocks(m["content"]):
                t = b.get("type")
                if t == "text" and b.get("text"):
                    parts.append({"text": b["text"]})
                elif t == "tool_use":
                    names[b["id"]] = b["name"]
                    call = {"name": b["name"], "args": b.get("input") or {}}
                    if not b["id"].startswith(GENERATED_ID_PREFIX):
                        call["id"] = b["id"]
                    parts.append({"functionCall": call,
                                  "thoughtSignature": self.signatures.get(b["id"], DUMMY_SIGNATURE)})
                elif t == "tool_result":
                    tool_id = b.get("tool_use_id", "")
                    resp = {"name": names.get(tool_id, ""), "response": _tool_response(b.get("content"))}
                    if not tool_id.startswith(GENERATED_ID_PREFIX):
                        resp["id"] = tool_id
                    parts.append({"functionResponse": resp})
            if parts:
                contents.append({"role": "model" if m["role"] == "assistant" else "user", "parts": parts})
        return contents

    def _request(self, payload: dict) -> dict:
        request: dict = {"contents": self._contents(payload.get("messages") or [])}
        system = _text_of(payload.get("system"))
        if system:
            request["systemInstruction"] = {"parts": [{"text": system}]}
        decls = []
        for tool in payload.get("tools") or []:
            decl = {"name": tool["name"], "description": tool.get("description", "")}
            schema = tool.get("input_schema") or {}
            if schema.get("properties"):  # Gemini не приймає об'єкт без полів
                decl["parameters"] = schema
            decls.append(decl)
        if decls:
            request["tools"] = [{"functionDeclarations": decls}]
            mode = "NONE" if (payload.get("tool_choice") or {}).get("type") == "none" else "AUTO"
            request["toolConfig"] = {"functionCallingConfig": {"mode": mode}}
        config: dict = {}
        if payload.get("max_tokens"):
            config["maxOutputTokens"] = payload["max_tokens"]
        thinking = self._thinking_config(payload)
        if thinking:
            config["thinkingConfig"] = thinking
        if config:
            request["generationConfig"] = config
        return request

    # ---------------------------------------------------------- Gemini → Claude
    def _response(self, data: dict) -> dict:
        usage = data.get("usageMetadata") or {}
        cached = usage.get("cachedContentTokenCount") or 0
        result = {
            "model": self.model,
            "content": [],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": (usage.get("promptTokenCount") or 0) - cached,
                "output_tokens": (usage.get("candidatesTokenCount") or 0) + (usage.get("thoughtsTokenCount") or 0),
                "cache_read_input_tokens": cached,
                "cache_creation_input_tokens": 0,
            },
        }
        candidates = data.get("candidates") or []
        if not candidates:
            if (data.get("promptFeedback") or {}).get("blockReason"):
                result["stop_reason"] = "refusal"
            return result
        candidate = candidates[0]
        has_calls = False
        for part in (candidate.get("content") or {}).get("parts") or []:
            if part.get("thought"):
                continue
            if "functionCall" in part:
                call = part["functionCall"]
                tool_id = call.get("id") or f"{GENERATED_ID_PREFIX}{uuid.uuid4().hex[:16]}"
                if part.get("thoughtSignature"):
                    self.signatures[tool_id] = part["thoughtSignature"]
                    while len(self.signatures) > 2000:
                        self.signatures.popitem(last=False)
                result["content"].append({"type": "tool_use", "id": tool_id, "name": call.get("name", ""),
                                          "input": call.get("args") or {}})
                has_calls = True
            elif part.get("text"):
                result["content"].append({"type": "text", "text": part["text"]})
        reason = candidate.get("finishReason")
        if has_calls:
            result["stop_reason"] = "tool_use"
        elif reason == "MAX_TOKENS":
            result["stop_reason"] = "max_tokens"
        elif reason in REFUSAL_REASONS:
            result["stop_reason"] = "refusal"
        return result

    # ---------------------------------------------------------- той самий інтерфейс, що й у ClaudeClient
    def create_sync(self, payload: dict) -> dict:
        return self._response(self._post("generateContent", self._request(payload)))

    async def create(self, payload: dict) -> dict:
        return await run_blocking(self.create_sync, payload)

    def count_tokens_sync(self, payload: dict) -> int:
        """Безкоштовна перевірка ключа й назви моделі."""
        request = self._request(payload)
        request.pop("generationConfig", None)
        request.pop("toolConfig", None)
        request["model"] = f"models/{self.model}"
        result = self._post("countTokens", {"generateContentRequest": request})
        return int(result.get("totalTokens", 0))


def make_llm(settings, retries: int = 2):
    """Клієнт AI за налаштуваннями (provider у settings.toml)."""
    if settings.provider == "gemini":
        return GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_api_base, retries=retries)
    return ClaudeClient(settings.anthropic_api_key, settings.anthropic_api_base, retries=retries)
