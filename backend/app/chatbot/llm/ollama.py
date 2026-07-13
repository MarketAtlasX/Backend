import json
import logging
from typing import Generator, Optional

import httpx

from .base import LLMInterface

logger = logging.getLogger(__name__)


class OllamaLLM(LLMInterface):
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._available = None

    def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            with httpx.Client(base_url=self.base_url, timeout=2) as client:
                resp = client.get("/api/tags")
                self._available = resp.status_code == 200
                return self._available
        except Exception:
            self._available = False
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        if not self._check_available():
            raise ConnectionError("Ollama not available")
        payload = {"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": temperature}}
        if system_prompt:
            payload["system"] = system_prompt
        with httpx.Client(base_url=self.base_url, timeout=120) as client:
            resp = client.post("/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Generator[str, None, None]:
        if not self._check_available():
            raise ConnectionError("Ollama not available")
        payload = {"model": self.model, "prompt": prompt, "stream": True, "options": {"temperature": temperature}}
        if system_prompt:
            payload["system"] = system_prompt
        with httpx.Client(base_url=self.base_url, timeout=60) as client:
            with client.stream("POST", "/api/generate", json=payload) as resp:
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
