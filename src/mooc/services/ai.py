"""Local AI provider — Ollama HTTP integration.

The platform calls a local Ollama instance (https://ollama.com) running
beside the application server so that all learner data stays inside the
Saudi data residency boundary required by NELC. The default model is a
lightweight Arabic-capable model that runs on commodity hardware
(``llama3.1:8b-instruct``); operators can override via env vars:

* ``MOOC_OLLAMA_URL``   — base URL (default ``http://localhost:11434``)
* ``MOOC_OLLAMA_MODEL`` — model tag (default ``llama3.1:8b-instruct``)
* ``MOOC_AI_TIMEOUT``   — request timeout seconds (default 30)

If Ollama is unreachable, :func:`chat` returns a graceful fallback
message in Arabic so the UI never breaks. This keeps the AI features
optional — the platform still functions if the operator hasn't set up
Ollama yet.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Iterable, List, Mapping

logger = logging.getLogger(__name__)


_FALLBACK_AR = (
    "تعذّر الاتصال بمساعد الذكاء الاصطناعي حالياً. تأكد من تشغيل Ollama "
    "على المنصة، أو راجع المعلم/الإدارة."
)


def _settings():
    return {
        "url": os.environ.get("MOOC_OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        "model": os.environ.get("MOOC_OLLAMA_MODEL", "llama3.1:8b-instruct"),
        "timeout": float(os.environ.get("MOOC_AI_TIMEOUT", "30")),
    }


def chat(
    messages: List[Mapping[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.3,
) -> str:
    """Send a chat completion to Ollama and return the assistant's text.

    ``messages`` is a list of ``{"role": "system|user|assistant",
    "content": "..."}`` mappings (OpenAI-style). On any error we log
    the cause and return :data:`_FALLBACK_AR` so callers don't have to
    write defensive code at every call site.
    """
    cfg = _settings()
    payload = {
        "model": model or cfg["model"],
        "messages": list(messages),
        "stream": False,
        "options": {"temperature": temperature},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{cfg['url']}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Ollama chat call failed: %s", exc)
        return _FALLBACK_AR
    except json.JSONDecodeError as exc:
        logger.warning("Ollama returned non-JSON response: %s", exc)
        return _FALLBACK_AR

    msg = (data.get("message") or {}).get("content")
    if not msg:
        return _FALLBACK_AR
    return msg.strip()


def is_available() -> bool:
    """Quick health probe — used by templates to hide the chat panel
    if the operator hasn't configured Ollama yet."""
    cfg = _settings()
    try:
        with urllib.request.urlopen(f"{cfg['url']}/api/tags", timeout=2.0):
            return True
    except Exception:
        return False
