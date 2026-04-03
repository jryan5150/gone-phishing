"""OpenAI GPT adapter."""

from __future__ import annotations

import logging
import time

from openai import OpenAI

from .base import LLMAdapter

logger = logging.getLogger(__name__)


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
        start = time.monotonic()
        full = [{"role": "system", "content": system}, *messages]
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=full,
        )
        elapsed = time.monotonic() - start
        usage = resp.usage
        if usage:
            logger.info(
                "openai model=%s in=%d out=%d %.1fs",
                self._model, usage.prompt_tokens, usage.completion_tokens, elapsed,
            )
        return resp.choices[0].message.content or ""

    @property
    def model_name(self) -> str:
        return self._model
