"""OpenAI GPT adapter."""

from __future__ import annotations

from openai import OpenAI

from .base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        full = [{"role": "system", "content": system}, *messages]
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=full,
        )
        return resp.choices[0].message.content or ""

    @property
    def model_name(self) -> str:
        return self._model
