"""Google Gemini adapter."""

from __future__ import annotations

import logging
import time

import google.generativeai as genai

from .base import LLMAdapter

logger = logging.getLogger(__name__)


class GeminiAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model_name = model
        self._model = genai.GenerativeModel(
            model_name=model,
            system_instruction=None,  # set per-call
        )

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        # Gemini uses system_instruction on the model, not in GenerationConfig
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
        )

        history = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
            for m in messages
        ]
        chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])

        start = time.monotonic()
        resp = chat.send_message(
            history[-1]["parts"][0] if history else "",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
            ),
        )
        elapsed = time.monotonic() - start
        logger.info("gemini model=%s %.1fs", self._model_name, elapsed)
        return resp.text

    @property
    def model_name(self) -> str:
        return self._model_name
