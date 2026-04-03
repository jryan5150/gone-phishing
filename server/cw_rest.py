"""
Direct ConnectWise Manage REST client — no MCP subprocess needed.

Lightweight alternative to cw_tools.py (MCP-based) for environments where
spawning a Node subprocess isn't practical (Railway, Docker, CI).

Only exposes the IRP-relevant subset: create ticket, add note, list boards.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from config import (
    CW_BASE_URL,
    CW_CLIENT_ID,
    CW_COMPANY_ID,
    CW_PRIVATE_KEY,
    CW_PUBLIC_KEY,
)

logger = logging.getLogger(__name__)

API_VERSION = "/v4_6_release/apis/3.0"
_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def is_configured() -> bool:
    """Check if CW credentials are present."""
    return all([CW_COMPANY_ID, CW_PUBLIC_KEY, CW_PRIVATE_KEY, CW_CLIENT_ID])


def _headers() -> dict[str, str]:
    token = base64.b64encode(
        f"{CW_COMPANY_ID}+{CW_PUBLIC_KEY}:{CW_PRIVATE_KEY}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {token}",
        "clientId": CW_CLIENT_ID,
        "Content-Type": "application/json",
    }


def _url(path: str) -> str:
    return f"{CW_BASE_URL.rstrip('/')}{API_VERSION}{path}"


def create_ticket(
    summary: str,
    board_id: int | None = None,
    company_id: int | None = None,
    description: str = "",
    priority_id: int | None = None,
) -> dict[str, Any]:
    """Create a CW Manage service ticket.

    Returns the created ticket dict on success, or an error dict.
    """
    if not is_configured():
        return {"error": "ConnectWise credentials not configured"}

    body: dict[str, Any] = {"summary": summary[:100]}  # CW summary max 100 chars

    if description:
        body["initialDescription"] = description

    if board_id:
        body["board"] = {"id": board_id}

    if company_id:
        body["company"] = {"id": company_id}

    if priority_id:
        body["priority"] = {"id": priority_id}

    try:
        resp = httpx.post(
            _url("/service/tickets"),
            json=body,
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        ticket = resp.json()
        logger.info("CW ticket created: #%s", ticket.get("id"))
        return {"success": True, "ticket": ticket}
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response else str(exc)
        logger.error("CW create_ticket failed (%s): %s", exc.response.status_code, detail)
        return {"error": f"CW API {exc.response.status_code}: {detail}"}
    except httpx.ConnectError:
        logger.warning("CW API unreachable at %s", CW_BASE_URL)
        return {"error": f"CW API unreachable at {CW_BASE_URL}"}
    except Exception as exc:
        logger.exception("CW create_ticket unexpected error")
        return {"error": str(exc)}


def add_ticket_note(
    ticket_id: int,
    text: str,
    internal: bool = True,
) -> dict[str, Any]:
    """Add a note to an existing CW ticket."""
    if not is_configured():
        return {"error": "ConnectWise credentials not configured"}

    body: dict[str, Any] = {
        "text": text,
        "internalAnalysisFlag": internal,
    }

    try:
        resp = httpx.post(
            _url(f"/service/tickets/{ticket_id}/notes"),
            json=body,
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return {"success": True, "note": resp.json()}
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response else str(exc)
        logger.error("CW add_note failed (%s): %s", exc.response.status_code, detail)
        return {"error": f"CW API {exc.response.status_code}: {detail}"}
    except Exception as exc:
        logger.exception("CW add_note unexpected error")
        return {"error": str(exc)}


def list_boards(limit: int = 25) -> dict[str, Any]:
    """List service boards — useful for resolving board IDs."""
    if not is_configured():
        return {"error": "ConnectWise credentials not configured"}

    try:
        resp = httpx.get(
            _url("/service/boards"),
            params={"pageSize": limit},
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return {"success": True, "boards": resp.json()}
    except Exception as exc:
        logger.exception("CW list_boards error")
        return {"error": str(exc)}
