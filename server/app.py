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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import CHAT_UI, HOST, PORT
from llm import chat_response, generate_action_plan
from vector_store import ingest_playbooks, list_playbooks, search_playbooks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("gone-phishing")

app = FastAPI(
    title="Gone-Phishing IRP Engine",
    version="0.2.0",
    description="AI-powered Incident Response Plan retrieval and action plan generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Request / response schemas ---------------------------------------------


class IncidentInput(BaseModel):
    description: str = Field(..., min_length=5, description="Free-text incident description")
    severity: str | None = Field(None, description="S1 / S2 / S3 / S4")
    affected_systems: str | None = Field(None, description="Affected systems")


class SearchInput(BaseModel):
    query: str = Field(..., min_length=2, description="Search query for playbooks")
    n_results: int = Field(5, ge=1, le=20)


class ChatInput(BaseModel):
    messages: list[dict[str, str]] = Field(..., description="Chat history")


# -- API endpoints -----------------------------------------------------------


@app.post("/api/incident")
async def handle_incident(body: IncidentInput) -> dict[str, Any]:
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
    except Exception as exc:
        logger.exception("Incident endpoint error")
        raise HTTPException(500, str(exc))


@app.post("/api/chat")
async def handle_chat(body: ChatInput) -> dict[str, str]:
    """Follow-up questions in chat context."""
    try:
        latest_user_msg = next(
            (m["content"] for m in reversed(body.messages) if m["role"] == "user"),
            "",
        )
        matches = search_playbooks(latest_user_msg, n_results=5) if latest_user_msg else []
        response = chat_response(messages=body.messages, playbook_context=matches or None)
        return {"response": response}
    except Exception as exc:
        logger.exception("Chat endpoint error")
        raise HTTPException(500, str(exc))


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
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/api/playbooks")
async def get_playbooks() -> dict[str, Any]:
    """List all ingested playbook types."""
    return {"playbooks": list_playbooks()}


@app.post("/api/ingest")
async def run_ingest() -> dict[str, Any]:
    """Ingest / re-ingest playbooks into ChromaDB."""
    return ingest_playbooks()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gone-phishing"}


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

    logger.info("Ingesting playbooks on startup...")
    result = ingest_playbooks()
    logger.info("Ready: %d files, %d chunks", result["files_ingested"], result["total_chunks"])

    uvicorn.run(app, host=HOST, port=PORT)
