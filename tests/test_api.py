"""API endpoint tests.

These hit the real FastAPI app with a real ChromaDB backend
(populated with actual playbook content). The only thing mocked
is the LLM — we don't want tests that cost money on every run.

Tests focus on behavior a user would actually encounter:
  - Does search rank the right playbook first?
  - Does the chat flow work across multiple turns?
  - Do validation rules reject garbage input?
  - Is ingestion idempotent (no duplicate chunks)?
"""

from unittest.mock import patch


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "gone-phishing"
    assert "checks" in body


def test_health_reports_chromadb_status(client):
    """After ingestion, ChromaDB should show playbooks > 0."""
    resp = client.get("/api/health")
    checks = {c["name"]: c for c in resp.json()["checks"]}
    assert checks["chromadb"]["ok"] is True
    assert checks["chromadb"]["playbooks"] > 0


# ---------------------------------------------------------------------------
# Playbook listing
# ---------------------------------------------------------------------------


def test_list_playbooks_not_empty(client):
    resp = client.get("/api/playbooks")
    assert resp.status_code == 200
    playbooks = resp.json()["playbooks"]
    assert len(playbooks) > 0


def test_playbooks_include_ransomware(client):
    """Sanity check — ransomware.md should always be ingested."""
    resp = client.get("/api/playbooks")
    types = [p["playbook_type"] for p in resp.json()["playbooks"]]
    assert "ransomware" in types


def test_playbooks_exclude_readme_and_template(client):
    """README.md and full-irp-template.md should be skipped."""
    resp = client.get("/api/playbooks")
    types = [p["playbook_type"] for p in resp.json()["playbooks"]]
    assert "README" not in types
    assert "full-irp-template" not in types


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


def test_search_returns_results(client):
    resp = client.post("/api/search", json={"query": "ransomware encrypted files"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0


def test_search_ransomware_ranks_ransomware_playbook_first(client):
    """A ransomware query should surface the ransomware playbook, not phishing."""
    resp = client.post(
        "/api/search",
        json={"query": "files encrypted with ransom note demanding bitcoin", "n_results": 3},
    )
    top_type = resp.json()["results"][0]["playbook_type"]
    assert top_type == "ransomware", f"Expected ransomware first, got {top_type}"


def test_search_phishing_ranks_phishing_playbook_first(client):
    resp = client.post(
        "/api/search",
        json={"query": "user clicked suspicious email link entered credentials", "n_results": 3},
    )
    top_type = resp.json()["results"][0]["playbook_type"]
    assert top_type == "phishing", f"Expected phishing first, got {top_type}"


def test_search_bec_ranks_bec_playbook_first(client):
    resp = client.post(
        "/api/search",
        json={"query": "fraudulent wire transfer CEO impersonation", "n_results": 3},
    )
    top_type = resp.json()["results"][0]["playbook_type"]
    assert top_type == "bec", f"Expected bec first, got {top_type}"


def test_search_respects_n_results(client):
    resp = client.post("/api/search", json={"query": "incident", "n_results": 2})
    assert len(resp.json()["results"]) == 2


def test_search_relevance_is_between_0_and_1(client):
    resp = client.post("/api/search", json={"query": "malware detected"})
    for r in resp.json()["results"]:
        assert 0 <= r["relevance"] <= 1, f"Relevance out of range: {r['relevance']}"


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def test_ingest_is_idempotent(client):
    """Re-ingesting should not duplicate chunks."""
    resp1 = client.post("/api/ingest")
    resp2 = client.post("/api/ingest")
    assert resp1.json()["total_chunks"] == resp2.json()["total_chunks"]


# ---------------------------------------------------------------------------
# Incident endpoint (LLM mocked)
# ---------------------------------------------------------------------------


def _fake_plan(*args, **kwargs):
    return "## Test Action Plan\n\n- [ ] **IR Lead**: Isolate affected systems"


def test_incident_returns_action_plan(client):
    with patch("app.generate_action_plan", side_effect=_fake_plan):
        resp = client.post(
            "/api/incident",
            json={"description": "User clicked phishing link and entered M365 credentials"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "action_plan" in body
    assert "matched_playbooks" in body
    assert len(body["matched_playbooks"]) > 0


def test_incident_returns_top3_matched_playbooks(client):
    with patch("app.generate_action_plan", side_effect=_fake_plan):
        resp = client.post(
            "/api/incident",
            json={"description": "Ransomware encrypted the file server, ransom note on screen"},
        )
    playbooks = resp.json()["matched_playbooks"]
    assert len(playbooks) <= 3
    for p in playbooks:
        assert "type" in p
        assert "relevance" in p


def test_incident_rejects_empty_description(client):
    resp = client.post("/api/incident", json={"description": ""})
    assert resp.status_code == 422


def test_incident_rejects_too_short_description(client):
    resp = client.post("/api/incident", json={"description": "hi"})
    assert resp.status_code == 422


def test_incident_accepts_optional_severity(client):
    with patch("app.generate_action_plan", side_effect=_fake_plan):
        resp = client.post(
            "/api/incident",
            json={
                "description": "Multiple workstations showing ransom notes",
                "severity": "S1",
                "affected_systems": "DC01, FS01, WS-ACCT-*",
            },
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Chat endpoint (LLM mocked)
# ---------------------------------------------------------------------------


def _fake_chat(*args, **kwargs):
    return "The next step would be to check for lateral movement indicators."


def test_chat_returns_response(client):
    with patch("app.chat_response", side_effect=_fake_chat):
        resp = client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "What should we check next?"},
                ]
            },
        )
    assert resp.status_code == 200
    assert "response" in resp.json()


def test_chat_handles_multi_turn_conversation(client):
    """Simulate a real chat — initial incident then follow-ups."""
    with patch("app.chat_response", side_effect=_fake_chat):
        resp = client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "A user clicked a phishing link"},
                    {"role": "assistant", "content": "Here is the action plan..."},
                    {"role": "user", "content": "Should we also check email forwarding rules?"},
                ]
            },
        )
    assert resp.status_code == 200
    assert len(resp.json()["response"]) > 0


def test_chat_with_empty_messages_returns_200(client):
    """Edge case: empty message list shouldn't crash."""
    with patch("app.chat_response", side_effect=_fake_chat):
        resp = client.post("/api/chat", json={"messages": []})
    # Should not 500 — either returns a response or a validation error
    assert resp.status_code in (200, 422)


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------


def test_search_rejects_single_char_query(client):
    resp = client.post("/api/search", json={"query": "x"})
    assert resp.status_code == 422


def test_search_rejects_n_results_over_20(client):
    resp = client.post("/api/search", json={"query": "ransomware", "n_results": 50})
    assert resp.status_code == 422


def test_search_rejects_n_results_zero(client):
    resp = client.post("/api/search", json={"query": "ransomware", "n_results": 0})
    assert resp.status_code == 422
