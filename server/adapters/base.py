"""Abstract interface every LLM adapter must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """Uniform completion interface — swap providers without touching call sites."""

    @abstractmethod
    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """Return the assistant's response text."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the model in use (for logging / diagnostics)."""
