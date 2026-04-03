"""Google Gemini adapter."""

from __future__ import annotations

import google.generativeai as genai

from .base import LLMAdapter


class GeminiAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model_name = model
        self._model = genai.GenerativeModel(model_name=model)

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        history = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
            for m in messages
        ]
        chat = self._model.start_chat(history=history[:-1] if len(history) > 1 else [])
        resp = chat.send_message(
            history[-1]["parts"][0] if history else "",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                system_instruction=system,
            ),
        )
        return resp.text

    @property
    def model_name(self) -> str:
        return self._model_name
