"""Ollama adapter — local models via REST API."""

from __future__ import annotations

import httpx

from .base import LLMAdapter


class OllamaAdapter(LLMAdapter):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        resp = httpx.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    @property
    def model_name(self) -> str:
        return self._model
