"""
BYOM adapter registry.

Set LLM_PROVIDER in .env to switch backends:
  anthropic | openai | gemini | ollama
"""

from __future__ import annotations

from .base import LLMAdapter


def get_adapter() -> LLMAdapter:
    """Instantiate the adapter specified by current config."""
    from config import (
        ANTHROPIC_API_KEY,
        GOOGLE_API_KEY,
        LLM_MODEL,
        LLM_PROVIDER,
        OLLAMA_BASE_URL,
        OLLAMA_MODEL,
        OPENAI_API_KEY,
    )

    match LLM_PROVIDER:
        case "anthropic":
            from .anthropic_adapter import AnthropicAdapter
            return AnthropicAdapter(api_key=ANTHROPIC_API_KEY, model=LLM_MODEL)
        case "openai":
            from .openai_adapter import OpenAIAdapter
            return OpenAIAdapter(api_key=OPENAI_API_KEY, model=LLM_MODEL)
        case "gemini":
            from .gemini_adapter import GeminiAdapter
            return GeminiAdapter(api_key=GOOGLE_API_KEY, model=LLM_MODEL)
        case "ollama":
            from .ollama_adapter import OllamaAdapter
            return OllamaAdapter(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)
        case _:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. "
                "Options: anthropic, openai, gemini, ollama"
            )


__all__ = ["LLMAdapter", "get_adapter"]
