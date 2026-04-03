"""Claude adapter (Anthropic SDK)."""

from __future__ import annotations

from anthropic import Anthropic

from .base import LLMAdapter


class AnthropicAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return resp.content[0].text

    @property
    def model_name(self) -> str:
        return self._model
