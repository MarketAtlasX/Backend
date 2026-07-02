import json
import logging
import random
import re
from typing import Generator, Optional

import httpx

from .base import LLMInterface
from .ollama import OllamaLLM
from .provider_gemini import HybridLLM

logger = logging.getLogger(__name__)

OPENAI_API_KEY: Optional[str] = None
CLAUDE_API_KEY: Optional[str] = None
LLM_MODEL = "gpt-4o-mini"

try:
    from app.config import settings as _s
except Exception:
    _s = None


def _load_keys():
    global OPENAI_API_KEY, CLAUDE_API_KEY
    if OPENAI_API_KEY is not None:
        return
    import os
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") or ""
    if not OPENAI_API_KEY:
        OPENAI_API_KEY = ""
    if not CLAUDE_API_KEY:
        CLAUDE_API_KEY = ""


class MarketAtlasLLM(LLMInterface):
    """LLM provider that tries OpenAI, then Claude, then Ollama, then Mock fallback."""

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        _load_keys()
        if OPENAI_API_KEY:
            try:
                return self._call_openai(prompt, system_prompt, temperature)
            except Exception as e:
                logger.warning(f"OpenAI failed, trying Claude: {e}")
        if CLAUDE_API_KEY:
            try:
                return self._call_claude(prompt, system_prompt, temperature)
            except Exception as e:
                logger.warning(f"Claude failed, trying Ollama: {e}")
        try:
            return OllamaLLM().generate(prompt, system_prompt, temperature)
        except Exception as e:
            logger.warning(f"Ollama failed, using MockLLM: {e}")
            return MockLLM().generate(prompt, system_prompt, temperature)

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        _load_keys()
        if OPENAI_API_KEY:
            try:
                yield from self._stream_openai(prompt, system_prompt, temperature)
                return
            except Exception:
                pass
        if CLAUDE_API_KEY:
            try:
                yield from self._stream_claude(prompt, system_prompt, temperature)
                return
            except Exception:
                pass
        try:
            yield from OllamaLLM().generate_stream(prompt, system_prompt, temperature)
        except Exception:
            yield from MockLLM().generate_stream(prompt, system_prompt, temperature)

    def _call_openai(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": LLM_MODEL, "messages": messages, "temperature": temperature, "max_tokens": 2000},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_claude(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 2000,
            "messages": messages,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    def _stream_openai(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        with httpx.Client(timeout=60) as client:
            with client.stream(
                "POST", "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": LLM_MODEL, "messages": messages, "temperature": temperature, "max_tokens": 2000, "stream": True},
            ) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta

    def _stream_claude(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 2000,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        with httpx.Client(timeout=60) as client:
            with client.stream(
                "POST", "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        chunk = json.loads(line[6:])
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {}).get("text", "")
                            if delta:
                                yield delta



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
            if "Extract geopolitical entities" in prompt or "Extract all named entities" in prompt:
                entities = []
                for word in query.split():
                    if word[0].isupper() and len(word) > 2:
                        entities.append(word.strip(".,;:!?"))
                if not entities:
                    entities = ["Iran", "Oil", "Energy"] if "oil" in query.lower() else ["Russia", "Europe", "Gas"]
                return json.dumps(list(set(entities[:5])))
            if "stock tickers" in prompt:
                tickers = []
                for word in query.split():
                    w = word.strip(".,;:!?").upper()
                    if len(w) <= 5 and w.isalpha() and w != word:
                        tickers.append(w)
                if not tickers:
                    tickers = ["XLE", "CVX", "XOM"] if "energy" in query.lower() or "oil" in query.lower() else ["SPY", "QQQ"]
                return json.dumps(tickers[:5])

        if "classify" in prompt.lower() or "category" in prompt.lower():
            keywords = {
                "oil": "IMPACT", "sanction": "NEWS", "buy": "RECOMMENDATION", "sell": "RECOMMENDATION",
                "invest": "RECOMMENDATION", "simulate": "SIMULATION", "what if": "SIMULATION",
                "scenario": "SIMULATION", "relationship": "GRAPH", "connection": "GRAPH",
                "report": "REPORT", "intelligence": "REPORT", "news": "NEWS", "latest": "NEWS",
                "price": "MARKET", "market": "MARKET", "stock": "MARKET",
                "country": "NEWS", "sanctions": "NEWS", "tariff": "NEWS",
            }
            q = query.lower()
            for kw, cat in keywords.items():
                if kw in q:
                    return cat
            if FOLLOWUP_PRONOUNS.search(q):
                for kw in ["sanction", "conflict", "war", "attack", "tension"]:
                    if kw in system_prompt or kw in prompt:
                        return "NEWS"
                return "IMPACT"
            return random.choice(["IMPACT", "NEWS"])

        return self._mock_response(query, system_prompt, prompt)

    def _mock_response(self, query: str, system_prompt: Optional[str] = None, full_prompt: str = "") -> str:
        q = query.lower()

        if "simulate" in q or "what if" in q or "scenario" in q:
            return json.dumps({
                "scenario": f"Scenario: {query}",
                "consequences": {"Oil": "+12%", "European Manufacturing": "-5%", "Inflation": "+2.3%"},
                "probability": 0.71,
                "time_horizon": "medium term",
                "key_risks": ["Supply chain disruption", "Inflation spike", "Market volatility"]
            })

        oil_keywords = ["oil", "energy", "crude", "gas", "petroleum"]
        defense_keywords = ["defense", "military", "lockheed", "northrop", "weapon"]
        sanction_keywords = ["sanction", "tariff", "trade war", "embargo"]
        conflict_keywords = ["conflict", "war", "attack", "tension", "strike", "blockade"]
        market_keywords = ["market", "stock", "price", "etf", "index", "rally", "decline"]

        if any(k in q for k in oil_keywords):
            return "Analysis indicates energy markets are experiencing upward pressure due to geopolitical tensions. Primary drivers include supply constraints, rising shipping costs, and increased risk premium. The energy sector shows strong momentum with elevated volatility suggesting continued uncertainty."
        if any(k in q for k in defense_keywords):
            return "Defense sector analysis shows increased demand expectations driven by rising geopolitical tensions. Key beneficiaries include major defense contractors. Safe-haven flows also support gold and energy ETFs."
        if any(k in q for k in sanction_keywords):
            return "Sanctions analysis indicates significant market disruption potential. Affected sectors include energy, finance, and shipping. Supply chain reconfiguration expected with medium-term inflationary pressure."
        if any(k in q for k in conflict_keywords):
            return "Geopolitical risk assessment shows elevated tension levels. Direct market impacts expected in energy, defense, and safe-haven assets. Confidence level: moderate to high based on current intelligence indicators."
        if any(k in q for k in market_keywords):
            return "Market analysis indicates mixed signals. Momentum shows positive trend but volatility remains elevated. Volume patterns suggest institutional positioning. Recommend monitoring key support levels."

        if FOLLOWUP_GREETINGS.match(q) or FOLLOWUP_PRONOUNS.search(q):
            if "country" in q or "nation" in q:
                return "Based on current sanctions analysis, Russia faces the most significant impact due to energy sector restrictions, followed by Iran (financial sanctions) and North Korea (comprehensive trade embargo). Key affected countries: Russia, Iran, North Korea, Venezuela, and Belarus."
            if "sector" in q or "industry" in q:
                return "The most affected sectors are Energy (crude oil exports down 15%), Financial Services (SWIFT disconnection impacts), Defense (increased NATO spending), and Shipping (Black Sea route disruptions)."
            if "most" in q or "worst" in q or "biggest" in q:
                return "The most significant impact is currently observed in the Russian energy sector, with crude export revenues down approximately 15%. Secondary effects are most pronounced in European manufacturing due to elevated natural gas prices."
            return "Based on the analysis above: Russia and Iran face the most severe sanctions impact. The energy sector is the most affected, with crude oil supply disruptions and price volatility. European manufacturing faces secondary impacts from elevated energy costs."

        if "report" in q or "intelligence" in q:
            return json.dumps({
                "title": "Geopolitical Intelligence Report",
                "event": f"Analysis of: {query}",
                "affected_sectors": ["Energy", "Defense", "Financials"],
                "risk_score": 0.72,
                "expected_market_impact": "Moderate to significant impact expected across affected sectors",
                "recommended_assets": ["XLE", "GDX", "TLT"],
                "confidence": 0.78,
                "reasoning": "Based on current geopolitical indicators and market positioning analysis",
                "sources": ["MarketAtlas Intelligence", "Reuters", "Bloomberg"]
            })

        return f"Analysis complete for: {query[:100]}... Assessment based on available intelligence indicates moderate geopolitical risk with potential market implications across affected sectors."

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        result = self.generate(prompt, system_prompt, temperature)
        for chunk in result.split(". "):
            yield chunk + ". "


def get_llm() -> LLMInterface:
    try:
        hybrid = HybridLLM()
        if hybrid._gemini_available:
            return hybrid
    except Exception:
        pass
    return MarketAtlasLLM()
