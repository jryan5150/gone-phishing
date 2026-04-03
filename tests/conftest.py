"""Shared test fixtures.

Uses a temporary directory for ChromaDB so tests never touch
the real vector store. Playbooks are ingested once per session.
"""

import os
import sys
import tempfile

import pytest

# Allow imports from server/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

# Point ChromaDB at a temp dir before anything imports config
_tmp_chroma = tempfile.mkdtemp(prefix="gp_test_chroma_")
os.environ.setdefault("CHROMA_DIR", _tmp_chroma)
os.environ.setdefault("LLM_PROVIDER", "anthropic")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-fake-key-for-tests")


@pytest.fixture(scope="session")
def ingested_playbooks():
    """Ingest the real playbooks once. Returns the summary dict."""
    from vector_store import ingest_playbooks

    result = ingest_playbooks()
    assert result["files_ingested"] > 0, "No playbooks found — check playbooks/ dir"
    return result


@pytest.fixture(scope="session")
def client(ingested_playbooks):
    """FastAPI TestClient with playbooks already loaded."""
    from fastapi.testclient import TestClient

    from app import app

    return TestClient(app)
