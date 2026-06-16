from abc import ABC, abstractmethod
from typing import Optional


class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        ...

    @abstractmethod
    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3):
        ...
