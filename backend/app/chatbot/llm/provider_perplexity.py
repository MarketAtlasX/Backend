"""Perplexity LLM provider for the MarketAtlas chatbot.

Perplexity's Sonar models perform live web search and return cited sources,
which gives the chatbot current, real-time knowledge. The API is
OpenAI-compatible (POST /chat/completions) with an additional `citations`
array on the response.
"""

import contextvars
import logging
import os
from typing import Generator, Optional

import httpx

from .base import LLMInterface

logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY: Optional[str] = None
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar-pro")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


def _get_model() -> str:
    try:
        from app.config import settings as _s
        if _s.perplexity_model:
            return _s.perplexity_model
    except Exception:
        pass
    return PERPLEXITY_MODEL


_citations_var: "contextvars.ContextVar[list[str]]" = contextvars.ContextVar(
    "perplexity_citations", default=[]
)


def _load_key():
    global PERPLEXITY_API_KEY
    if PERPLEXITY_API_KEY is None:
        PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY") or ""
        try:
            from app.config import settings as _s
            if not PERPLEXITY_API_KEY:
                PERPLEXITY_API_KEY = _s.perplexity_api_key or ""
        except Exception:
            pass


def get_last_citations() -> list[str]:
    """Return citations collected for the current request/context."""
    return list(_citations_var.get())


def _store_citations(data: dict) -> None:
    _citations_var.set(list(data.get("citations", []) or []))


def clear_citations() -> None:
    """Reset citations for the current context (per-request isolation)."""
    _citations_var.set([])


def _build_messages(
    prompt: str,
    system_prompt: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> list[dict]:
    """Assemble chat messages: system prompt, prior turns, then the current query."""
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("system", "user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})
    return messages


class PerplexityLLM(LLMInterface):
    def __init__(self, model: Optional[str] = None):
        self.model = model or _get_model()
        _load_key()

    def available(self) -> bool:
        _load_key()
        return bool(PERPLEXITY_API_KEY)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, history: Optional[list[dict]] = None) -> str:
        _load_key()
        if not PERPLEXITY_API_KEY:
            raise ConnectionError("Perplexity API key not configured")

        messages = _build_messages(prompt, system_prompt, history)

        try:
            with httpx.Client(timeout=45) as client:
                resp = client.post(
                    PERPLEXITY_URL,
                    headers={
                        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2048,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                _store_citations(data)
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.warning("Perplexity API call failed: %s", e)
            raise

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, history: Optional[list[dict]] = None) -> Generator[str, None, None]:
        _load_key()
        if not PERPLEXITY_API_KEY:
            raise ConnectionError("Perplexity API key not configured")

        messages = _build_messages(prompt, system_prompt, history)

        try:
            with httpx.Client(timeout=90) as client:
                with client.stream(
                    "POST",
                    PERPLEXITY_URL,
                    headers={
                        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2048,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        if line == "data: [DONE]":
                            break
                        chunk = __import__("json").loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
        except Exception:
            yield ""
