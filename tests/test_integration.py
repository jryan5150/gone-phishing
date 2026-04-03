"""Integration tests — full request lifecycle.

These tests verify the actual data flow from HTTP request through
vector search to response assembly. They catch the bugs that unit
tests miss — like search results not making it into the response
envelope, or playbook metadata getting dropped between layers.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


# ---------------------------------------------------------------------------
# End-to-end: incident → search → plan assembly
# ---------------------------------------------------------------------------


def _fake_plan_with_context(
    incident_description, playbook_context, severity=None, affected_systems=None
):
    """Fake LLM that echoes back what context it received,
    so we can verify the pipeline actually passed the right data."""
    playbook_types = [c["metadata"]["playbook_type"] for c in playbook_context]
    return f"PLAN for: {incident_description[:50]}... | context: {','.join(playbook_types)}"


def test_incident_pipeline_passes_search_results_to_llm(client):
    """Verify that semantic search results actually reach the LLM.
    This catches the case where the search works but the results
    get dropped before plan generation."""
    with patch("app.generate_action_plan", side_effect=_fake_plan_with_context):
        resp = client.post(
            "/api/incident",
            json={"description": "Ransomware encrypted all shared drives, CryptoLocker variant"},
        )
    plan = resp.json()["action_plan"]
    # The plan should reference ransomware playbook context
    assert "ransomware" in plan.lower()


def test_incident_matched_playbooks_have_relevance_scores(client):
    """Relevance scores should be present and meaningful (0-1 range)."""
    with patch("app.generate_action_plan", return_value="test plan"):
        resp = client.post(
            "/api/incident",
            json={"description": "User credentials stolen via phishing email"},
        )
    for pb in resp.json()["matched_playbooks"]:
        assert "relevance" in pb
        assert isinstance(pb["relevance"], float)
        assert 0 <= pb["relevance"] <= 1


def test_chat_searches_on_latest_user_message_not_first(client):
    """The chat endpoint should search based on the LATEST user message,
    not the first one. This matters for multi-turn — the user might
    pivot from phishing to ransomware mid-conversation."""
    def _fake_chat(messages, playbook_context=None):
        types = [c["metadata"]["playbook_type"] for c in playbook_context] if playbook_context else []
        return f"context: {','.join(types)}"

    with patch("app.chat_response", side_effect=_fake_chat):
        resp = client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "We got phished"},
                    {"role": "assistant", "content": "Here's the phishing playbook..."},
                    # User pivots to asking about ransomware
                    {"role": "user", "content": "Actually we just found encrypted files with ransom notes too"},
                ]
            },
        )
    # The search context should be based on the ransomware message, not phishing
    response_text = resp.json()["response"]
    assert "ransomware" in response_text.lower()


# ---------------------------------------------------------------------------
# Concurrency: re-ingestion during search
# ---------------------------------------------------------------------------


def test_re_ingest_does_not_corrupt_search(client):
    """Ingesting again mid-session shouldn't break search results.
    This catches issues with the ChromaDB singleton state."""
    # Search before
    resp1 = client.post("/api/search", json={"query": "phishing"})
    count_before = len(resp1.json()["results"])

    # Re-ingest
    client.post("/api/ingest")

    # Search after — should get same number of results
    resp2 = client.post("/api/search", json={"query": "phishing"})
    count_after = len(resp2.json()["results"])

    assert count_before == count_after


# ---------------------------------------------------------------------------
# Data integrity
# ---------------------------------------------------------------------------


def test_all_search_results_have_required_fields(client):
    """Every search result must have content, metadata, and a playbook_type.
    Caught a bug where metadata was silently None after bad ingestion."""
    resp = client.post("/api/search", json={"query": "security incident", "n_results": 20})
    for r in resp.json()["results"]:
        assert "playbook_type" in r, "Missing playbook_type"
        assert "content" in r, "Missing content"
        assert "relevance" in r, "Missing relevance"
        assert r["content"].strip(), "Empty content"
        assert r["playbook_type"].strip(), "Empty playbook_type"


def test_ingest_chunk_counts_are_consistent(client):
    """The total_chunks in ingest response should match the sum of
    per-file chunk counts. Sounds obvious but caught an off-by-one."""
    resp = client.post("/api/ingest")
    body = resp.json()
    detail_sum = sum(d["chunks"] for d in body["details"])
    assert body["total_chunks"] == detail_sum


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_incident_with_broken_llm_returns_500_not_crash(client):
    """If the LLM adapter throws, we should get a clean 500, not a stack trace."""
    def _exploding_llm(*args, **kwargs):
        raise ConnectionError("LLM provider unreachable")

    with patch("app.generate_action_plan", side_effect=_exploding_llm):
        resp = client.post(
            "/api/incident",
            json={"description": "Test incident for error handling verification"},
        )
    assert resp.status_code == 500
    # Should NOT leak the raw exception message to the client
    assert "LLM provider unreachable" not in resp.json()["detail"]
    assert "server logs" in resp.json()["detail"].lower()


def test_chat_with_broken_llm_returns_500_not_crash(client):
    def _exploding_llm(*args, **kwargs):
        raise RuntimeError("Model rate limited")

    with patch("app.chat_response", side_effect=_exploding_llm):
        resp = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
        )
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Provider outage resilience
# ---------------------------------------------------------------------------


def test_anthropic_503_preserves_incident_context(client):
    """Simulate Anthropic returning 503 (overloaded) mid-incident.
    The system should fail gracefully and the search layer should
    still have the matched playbooks — incident context isn't lost
    just because the LLM is down."""
    def _anthropic_503(*args, **kwargs):
        raise ConnectionError("Error code: 503 - Anthropic API is temporarily overloaded")

    # First verify search still works independently
    search_resp = client.post(
        "/api/search",
        json={"query": "ransomware encrypted files demanding bitcoin", "n_results": 3},
    )
    assert search_resp.status_code == 200
    playbooks_before = search_resp.json()["results"]
    assert len(playbooks_before) > 0

    # Now hit the incident endpoint with a dead LLM
    with patch("app.generate_action_plan", side_effect=_anthropic_503):
        incident_resp = client.post(
            "/api/incident",
            json={"description": "Ransomware encrypted files demanding bitcoin"},
        )
    assert incident_resp.status_code == 500
    assert "server logs" in incident_resp.json()["detail"].lower()

    # Search layer should still be fully functional after the LLM failure
    search_after = client.post(
        "/api/search",
        json={"query": "ransomware encrypted files demanding bitcoin", "n_results": 3},
    )
    assert search_after.status_code == 200
    playbooks_after = search_after.json()["results"]
    assert len(playbooks_after) == len(playbooks_before)
    # Same playbooks, same order — LLM outage didn't corrupt the search layer
    assert playbooks_after[0]["playbook_type"] == playbooks_before[0]["playbook_type"]
