"""Claude adapter (Anthropic SDK)."""

from __future__ import annotations

import logging
import time

from anthropic import Anthropic

from .base import LLMAdapter

logger = logging.getLogger(__name__)


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
        start = time.monotonic()
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        elapsed = time.monotonic() - start
        tokens_in = resp.usage.input_tokens
        tokens_out = resp.usage.output_tokens
        logger.info(
            "anthropic model=%s in=%d out=%d %.1fs",
            self._model, tokens_in, tokens_out, elapsed,
        )
        return resp.content[0].text

    @property
    def model_name(self) -> str:
        return self._model
