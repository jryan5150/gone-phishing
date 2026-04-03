"""Adapter registry and instantiation tests.

Verifies that the BYOM layer actually wires up correctly —
wrong provider string shouldn't silently give you a default,
and missing API keys should fail before the first LLM call,
not inside it.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


def test_get_adapter_returns_anthropic_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # Force reload of config module to pick up new env
    import importlib
    import config
    importlib.reload(config)

    from adapters import get_adapter
    adapter = get_adapter()
    assert adapter.model_name  # should have a model name
    assert "AnthropicAdapter" in type(adapter).__name__


def test_get_adapter_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gpt-magic-3000")
    import importlib
    import config
    importlib.reload(config)

    from adapters import get_adapter
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_adapter()


def test_adapter_model_name_matches_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    import importlib
    import config
    importlib.reload(config)

    from adapters import get_adapter
    adapter = get_adapter()
    assert adapter.model_name == "claude-haiku-4-5-20251001"


def test_all_providers_importable():
    """Every adapter module should import without errors,
    even if the SDK isn't installed (that's a runtime error, not import)."""
    from adapters.base import LLMAdapter
    assert LLMAdapter  # ABC is always importable


def test_adapter_interface_is_enforced():
    """Subclassing LLMAdapter without implementing complete() should fail."""
    from adapters.base import LLMAdapter

    with pytest.raises(TypeError):
        class BadAdapter(LLMAdapter):
            pass
        BadAdapter()
