"""
Gone-Phishing — FastAPI server.

Serves the IRP API and, depending on CHAT_UI, mounts one of:
  builtin   → static web/index.html  (default, zero deps)
  chainlit  → Chainlit mounted at /chat
  gradio    → Gradio Block mounted at /chat
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import CHAT_UI, HOST, PORT, validate
from cw_rest import add_ticket_note, create_ticket, is_configured as cw_configured
from llm import chat_response, generate_action_plan
from tools.n8n_tools import tool_trigger_escalation
from vector_store import ingest_playbooks, list_playbooks, search_playbooks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("gone-phishing")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Gone-Phishing IRP Engine",
    version="0.2.0",
    description="AI-powered Incident Response Plan retrieval and action plan generation.",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})

_cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
_cors_origins = [o.strip() for o in _cors_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# -- Request / response schemas ---------------------------------------------


class IncidentInput(BaseModel):
    description: str = Field(..., min_length=5, description="Free-text incident description")
    severity: str | None = Field(None, description="S1 / S2 / S3 / S4")
    affected_systems: str | None = Field(None, description="Affected systems")
    create_ticket: bool = Field(True, description="Auto-create CW ticket")
    escalate: bool = Field(True, description="Fire N8N escalation chain")


class SearchInput(BaseModel):
    query: str = Field(..., min_length=2, description="Search query for playbooks")
    n_results: int = Field(5, ge=1, le=20)


class ChatInput(BaseModel):
    messages: list[dict[str, str]] = Field(..., description="Chat history")


# -- API endpoints -----------------------------------------------------------


@app.post("/api/incident")
@limiter.limit("10/minute")
async def handle_incident(request: Request, body: IncidentInput) -> dict[str, Any]:
    """Submit an incident description → receive a role-assigned action plan."""
    try:
        matches = search_playbooks(body.description, n_results=8)
        if not matches:
            raise HTTPException(404, "No playbooks found. Run POST /api/ingest first.")

        plan = generate_action_plan(
            incident_description=body.description,
            playbook_context=matches,
            severity=body.severity,
            affected_systems=body.affected_systems,
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
    except HTTPException:
        raise
    except Exception:
        logger.exception("Incident endpoint error")
        raise HTTPException(500, "Failed to generate action plan. Check server logs.")


@app.post("/api/incident/respond")
async def handle_incident_respond(body: IncidentInput) -> dict[str, Any]:
    """Full pipeline: incident → action plan → CW ticket → N8N escalation.

    This is the demo endpoint that chains all three systems together.
    Each step degrades gracefully if its backing service is unavailable.
    """
    result: dict[str, Any] = {
        "action_plan": None,
        "matched_playbooks": [],
        "cw_ticket": None,
        "escalation": None,
    }

    # Step 1: Generate action plan (same as /api/incident)
    try:
        matches = search_playbooks(body.description, n_results=8)
        if not matches:
            raise HTTPException(404, "No playbooks found. Run POST /api/ingest first.")

        plan = generate_action_plan(
            incident_description=body.description,
            playbook_context=matches,
            severity=body.severity,
            affected_systems=body.affected_systems,
        )
        result["action_plan"] = plan
        result["matched_playbooks"] = [
            {
                "type": m["metadata"]["playbook_type"],
                "relevance": round(1 - (m["distance"] or 0), 3),
            }
            for m in matches[:3]
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Action plan generation failed")
        raise HTTPException(500, f"Plan generation failed: {exc}")

    # Classify for downstream (extract severity from plan if not provided)
    severity = body.severity or "S2"
    ticket_summary = f"[IRP] {body.description[:80]}"

    # Step 2: Create CW ticket (graceful degradation)
    if body.create_ticket and cw_configured():
        try:
            ticket_result = create_ticket(
                summary=ticket_summary,
                description=body.description,
            )
            if ticket_result.get("success"):
                ticket = ticket_result["ticket"]
                ticket_id = ticket["id"]
                result["cw_ticket"] = {
                    "id": ticket_id,
                    "summary": ticket.get("summary"),
                }

                # Add the full action plan as an internal note
                note_result = add_ticket_note(
                    ticket_id=ticket_id,
                    text=f"## AI-Generated Action Plan\n\n{plan}",
                    internal=True,
                )
                if note_result.get("error"):
                    logger.warning("CW note failed: %s", note_result["error"])
            else:
                result["cw_ticket"] = {"error": ticket_result.get("error", "Unknown error")}
        except Exception as exc:
            logger.exception("CW ticket creation failed")
            result["cw_ticket"] = {"error": str(exc)}
    elif not cw_configured():
        result["cw_ticket"] = {"error": "CW credentials not configured"}

    # Step 3: Fire N8N escalation (graceful degradation)
    if body.escalate:
        try:
            incident_id = f"IRP-{result['cw_ticket']['id']}" if result["cw_ticket"] and result["cw_ticket"].get("id") else "IRP-UNTRACKED"
            escalation = tool_trigger_escalation(
                incident_id=incident_id,
                severity=severity,
                summary=ticket_summary,
            )
            result["escalation"] = escalation
        except Exception as exc:
            logger.exception("N8N escalation failed")
            result["escalation"] = {"status": "error", "error": str(exc)}

    return result


@app.post("/api/chat")
@limiter.limit("20/minute")
async def handle_chat(request: Request, body: ChatInput) -> dict[str, str]:
    """Follow-up questions in chat context."""
    try:
        latest_user_msg = next(
            (m["content"] for m in reversed(body.messages) if m["role"] == "user"),
            "",
        )
        matches = search_playbooks(latest_user_msg, n_results=5) if latest_user_msg else []
        response = chat_response(messages=body.messages, playbook_context=matches or None)
        return {"response": response}
    except Exception:
        logger.exception("Chat endpoint error")
        raise HTTPException(500, "Chat request failed. Check server logs.")


@app.post("/api/search")
async def handle_search(body: SearchInput) -> dict[str, Any]:
    """Direct playbook semantic search."""
    try:
        matches = search_playbooks(body.query, n_results=body.n_results)
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
    except Exception:
        logger.exception("Search endpoint error")
        raise HTTPException(500, "Search failed. Check server logs.")


@app.get("/api/playbooks")
async def get_playbooks() -> dict[str, Any]:
    """List all ingested playbook types."""
    return {"playbooks": list_playbooks()}


@app.post("/api/ingest")
async def run_ingest() -> dict[str, Any]:
    """Ingest / re-ingest playbooks into ChromaDB."""
    return ingest_playbooks()


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Liveness check with dependency status."""
    checks: list[dict[str, Any]] = []

    # ChromaDB reachable + playbooks ingested
    try:
        playbooks = list_playbooks()
        checks.append({"name": "chromadb", "ok": True, "playbooks": len(playbooks)})
    except Exception as exc:
        checks.append({"name": "chromadb", "ok": False, "error": str(exc)})

    # LLM provider configured
    from config import LLM_MODEL, LLM_PROVIDER
    llm_configured = True
    try:
        from adapters import get_adapter
        adapter = get_adapter()
        checks.append({"name": "llm", "ok": True, "provider": LLM_PROVIDER, "model": adapter.model_name})
    except Exception as exc:
        llm_configured = False
        checks.append({"name": "llm", "ok": False, "error": str(exc)})

    all_ok = all(c["ok"] for c in checks)
    return {
        "status": "ok" if all_ok else "degraded",
        "service": "gone-phishing",
        "checks": checks,
    }


# -- Chat UI mount -----------------------------------------------------------

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")


def _mount_builtin() -> None:
    """Serve the bundled single-file chat UI."""

    @app.get("/")
    async def serve_ui():
        return FileResponse(os.path.join(WEB_DIR, "index.html"))

    if os.path.exists(WEB_DIR):
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    logger.info("Chat UI: builtin (web/index.html)")


def _mount_chainlit() -> None:
    """Mount Chainlit as a FastAPI sub-application at /chat."""
    try:
        from chainlit.utils import mount_chainlit

        cl_app = os.path.join(os.path.dirname(__file__), "cl_app.py")
        mount_chainlit(app=app, target=cl_app, path="/chat")
        logger.info("Chat UI: Chainlit mounted at /chat")
    except ImportError:
        logger.warning("chainlit not installed — falling back to builtin UI")
        _mount_builtin()


match CHAT_UI:
    case "chainlit":
        _mount_chainlit()
    case _:
        _mount_builtin()


# -- Entrypoint --------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    validate()
    logger.info("Ingesting playbooks on startup...")
    result = ingest_playbooks()
    logger.info("Ready: %d files, %d chunks", result["files_ingested"], result["total_chunks"])

    uvicorn.run(app, host=HOST, port=PORT)
