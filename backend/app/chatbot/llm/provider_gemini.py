"""Gemini LLM provider with Ollama fallback for the MarketAtlas chatbot.

Tries Gemini API (gemini-2.0-flash) first, falls back to Ollama (qwen2.5:7b),
then to the MockLLM if neither is available.
"""

import json
import logging
import os
import re
from typing import Generator, Optional

import httpx

from .base import LLMInterface
from .ollama import OllamaLLM

logger = logging.getLogger(__name__)

GEMINI_API_KEY: Optional[str] = None
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _load_gemini_key():
    global GEMINI_API_KEY
    if GEMINI_API_KEY is not None:
        return
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or ""


class GeminiLLM(LLMInterface):
    def __init__(self, model: str = GEMINI_MODEL):
        self.model = model

    def _available(self) -> bool:
        _load_gemini_key()
        return bool(GEMINI_API_KEY)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        _load_gemini_key()
        if not GEMINI_API_KEY:
            raise ConnectionError("Gemini API key not configured")
        url = f"{GEMINI_BASE}/models/{self.model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2000,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return ""
        except Exception as e:
            logger.warning("Gemini API call failed: %s", e)
            raise

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        _load_gemini_key()
        if not GEMINI_API_KEY:
            raise ConnectionError("Gemini API key not configured")
        url = f"{GEMINI_BASE}/models/{self.model}:streamGenerateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2000,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                for candidate in data:
                    parts = candidate.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield text
        except Exception:
            yield ""


FOLLOWUP_GREETINGS = re.compile(
    r"^(what|which|who|where|why|how|tell me more|"
    r"can you|could you|what about|how about|and|so|"
    r"i asked|that is|it is|they are|these are)",
    re.IGNORECASE,
)
FOLLOWUP_PRONOUNS = re.compile(
    r"\b(it|they|them|this|that|those|these|its|their|the|"
    r"country|countries|sector|sectors|region|regions|"
    r"one|ones|most|more|specifically|exactly|precisely)\b",
    re.IGNORECASE,
)


class MockLLM(LLMInterface):
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        query = prompt.split("Query: ")[-1].split("\n")[0].strip() if "Query: " in prompt else prompt[:100]
        if "Extract" in prompt or "JSON" in prompt:
            if "geopolitical entities" in prompt or "named entities" in prompt:
                entities = [w.strip(".,;:!?").capitalize() for w in query.split() if w[0].isupper() and len(w) > 2]
                return json.dumps(list(set(entities[:5] or ["Iran", "Oil", "Energy"])))
            if "stock tickers" in prompt:
                words = [w.strip(".,;:!?").upper() for w in query.split() if w.strip(".,;:!?").isalpha() and len(w.strip(".,;:!?")) <= 5]
                return json.dumps(words[:5] or ["SPY", "QQQ"])
        if "classify" in prompt.lower() or "category" in prompt.lower():
            ql = query.lower()
            kws = {
                "oil": "IMPACT", "sanction": "NEWS", "buy": "RECOMMENDATION", "sell": "RECOMMENDATION",
                "invest": "RECOMMENDATION", "simulate": "SIMULATION", "what if": "SIMULATION",
                "scenario": "SIMULATION", "relationship": "GRAPH", "connection": "GRAPH",
                "report": "REPORT", "intelligence": "REPORT", "news": "NEWS", "latest": "NEWS",
                "price": "MARKET", "market": "MARKET", "stock": "MARKET", "country": "NEWS",
                "sanctions": "NEWS", "tariff": "NEWS", "similar": "SIMILARITY",
                "historical": "SIMILARITY", "analogous": "SIMILARITY", "parallels": "SIMILARITY",
            }
            for kw, cat in kws.items():
                if kw in ql:
                    return cat
            if FOLLOWUP_PRONOUNS.search(ql):
                return "IMPACT"
            return "NEWS"
        return self._mock_response(query, system_prompt, prompt)

    def _mock_response(self, query: str, system_prompt: Optional[str] = None, full_prompt: str = "") -> str:
        q = query.lower()
        if "simulate" in q or "what if" in q or "scenario" in q:
            return json.dumps({
                "scenario": f"Scenario: {query}",
                "consequences": {"Oil": "+12%", "European Manufacturing": "-5%", "Inflation": "+2.3%"},
                "probability": 0.71, "time_horizon": "medium term",
                "key_risks": ["Supply chain disruption", "Inflation spike", "Market volatility"],
            })
        if any(kw in q for kw in ("oil", "energy", "crude", "gas")):
            return "Energy markets are under upward pressure due to geopolitical tensions. Supply constraints, rising shipping costs, and increased risk premium are the primary drivers. The sector shows strong momentum with elevated volatility suggesting continued uncertainty."
        if any(kw in q for kw in ("defense", "military", "lockheed", "weapon")):
            return "The defense sector shows increased demand expectations driven by rising geopolitical tensions. Key beneficiaries include major defense contractors. Safe-haven flows also support gold and energy ETFs."
        if any(kw in q for kw in ("sanction", "tariff", "trade war", "embargo")):
            return "Sanctions analysis indicates significant market disruption potential across energy, finance, and shipping. Supply chain reconfiguration expected with medium-term inflationary pressure."
        if any(kw in q for kw in ("conflict", "war", "attack", "tension", "strike")):
            return "Geopolitical risk assessment shows elevated tension levels. Direct market impacts expected in energy, defense, and safe-haven assets. Confidence level: moderate to high based on current intelligence indicators."
        if any(kw in q for kw in ("stock", "price", "market", "etf", "index")):
            return "Market analysis indicates mixed signals. Momentum shows a positive trend but volatility remains elevated. Volume patterns suggest institutional positioning. Recommend monitoring key support levels."
        if "report" in q or "intelligence" in q:
            return json.dumps({
                "title": "Geopolitical Intelligence Report",
                "event": f"Analysis of: {query}",
                "affected_sectors": ["Energy", "Defense", "Financials"],
                "risk_score": 0.72, "expected_market_impact": "Moderate to significant impact expected",
                "recommended_assets": ["XLE", "GDX", "TLT"],
                "confidence": 0.78, "reasoning": "Based on current geopolitical indicators and market positioning",
                "sources": ["MarketAtlas Intelligence", "Reuters", "Bloomberg"],
            })
        return f"Analysis complete for: {query[:100]}... Assessment based on available intelligence indicates moderate geopolitical risk with potential market implications."

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        result = self.generate(prompt, system_prompt, temperature)
        for chunk in result.split(". "):
            yield chunk + ". "


class HybridLLM(LLMInterface):
    """Tries Gemini API first, then Ollama, then Mock fallback."""

    def __init__(self):
        self._llm = None

    def _try_gemini(self) -> bool:
        _load_gemini_key()
        return bool(GEMINI_API_KEY)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        if self._try_gemini():
            try:
                return GeminiLLM().generate(prompt, system_prompt, temperature)
            except Exception as e:
                logger.warning("Gemini failed, falling back to Ollama: %s", e)
        try:
            return OllamaLLM().generate(prompt, system_prompt, temperature)
        except Exception as e:
            logger.warning("Ollama failed, using MockLLM: %s", e)
            return MockLLM().generate(prompt, system_prompt, temperature)

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        if self._try_gemini():
            try:
                yield from GeminiLLM().generate_stream(prompt, system_prompt, temperature)
                return
            except Exception:
                pass
        try:
            yield from OllamaLLM().generate_stream(prompt, system_prompt, temperature)
        except Exception:
            yield from MockLLM().generate_stream(prompt, system_prompt, temperature)


def get_llm() -> LLMInterface:
    return HybridLLM()
