"""
Core IRP tools — search, plan generation, playbook listing.

Each function is designed as a standalone unit that can be exposed directly
as an MCP tool or called from the FastAPI endpoints.
"""

from __future__ import annotations

from typing import Any

from adapters import get_adapter
from llm import SYSTEM_PROMPT, generate_action_plan
from vector_store import ingest_playbooks, list_playbooks, search_playbooks


def tool_search_playbooks(query: str, n_results: int = 5) -> dict[str, Any]:
    """Semantic search across ingested IRP playbooks."""
    matches = search_playbooks(query, n_results=n_results)
    return {
        "results": [
            {
                "playbook_type": m["metadata"]["playbook_type"],
                "content": m["content"],
                "relevance": round(1 - (m["distance"] or 0), 3),
            }
            for m in matches
        ]
    }


def tool_generate_action_plan(
    incident_description: str,
    severity: str | None = None,
    affected_systems: str | None = None,
) -> dict[str, Any]:
    """Generate a prioritised incident response action plan."""
    matches = search_playbooks(incident_description, n_results=8)
    if not matches:
        return {"error": "No playbooks ingested. Hit POST /api/ingest first."}

    plan = generate_action_plan(
        incident_description=incident_description,
        playbook_context=matches,
        severity=severity,
        affected_systems=affected_systems,
    )
    return {
        "action_plan": plan,
        "matched_playbooks": [
            {
                "type": m["metadata"]["playbook_type"],
                "relevance": round(1 - (m["distance"] or 0), 3),
            }
            for m in matches[:3]
        ],
    }


def tool_list_playbooks() -> dict[str, Any]:
    """List every ingested playbook type."""
    return {"playbooks": list_playbooks()}
