"""Minimal OpenAI-compatible client for the hosted Otari gateway (otari.ai).

Stdlib only. Base URL defaults to https://api.otari.ai/api/v1 (note the /api:
leaving it off is the most common mistake per Otari's API reference). The key is
read from OTARI_API_KEY and never logged.

Otari-run tools are declared by type: {"type": "otari_web_fetch"},
{"type": "otari_web_search"}, {"type": "otari_code_execution"}. Otari executes them
inside the request and reports what it ran in `otari_tool_calls`.

Model fallback: a list of open-weight models is tried in order; each attempt is
recorded so the report shows which model answered and which failed.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "https://api.otari.ai/api/v1"


class OtariClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 models: list[str] | None = None, timeout: float = 180.0) -> None:
        self.base = (base_url or os.environ.get("OTARI_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("OTARI_API_KEY")
        env_models = [m.strip() for m in (os.environ.get("OTARI_MODELS") or "").split(",") if m.strip()]
        self.models = models or env_models
        self.timeout = timeout

    def _post(self, path: str, body: dict[str, Any]) -> tuple[int | None, Any, str | None]:
        headers = {"content-type": "application/json", "accept": "application/json"}
        if self.api_key:
            headers["authorization"] = "Bearer " + self.api_key
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace")), None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            return exc.code, None, "http " + str(exc.code) + ": " + raw[:300]
        except Exception as exc:
            return None, None, type(exc).__name__ + ": " + str(exc)[:300]

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
             extra_headers: dict[str, str] | None = None, max_tokens: int = 4000) -> dict[str, Any]:
        attempts: list[dict[str, Any]] = []
        if not self.models:
            return {"ok": False, "error": "no model configured (set OTARI_MODELS)", "attempts": attempts}
        for model in self.models:
            body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens}
            if tools:
                body["tools"] = tools
            started = time.monotonic()
            code, data, err = self._post("/chat/completions", body)
            ms = int((time.monotonic() - started) * 1000)
            if data and data.get("choices"):
                msg = data["choices"][0].get("message") or {}
                attempts.append({"model": model, "ok": True, "http_status": code, "ms": ms})
                return {"ok": True, "model": model, "content": (msg.get("content") or "").strip(),
                        "otari_tool_calls": data.get("otari_tool_calls") or [], "usage": data.get("usage"),
                        "attempts": attempts}
            attempts.append({"model": model, "ok": False, "http_status": code, "ms": ms, "error": err or "no choices"})
        return {"ok": False, "error": "every model failed", "attempts": attempts}
