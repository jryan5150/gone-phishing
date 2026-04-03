"""
ConnectWise Manage integration — MCP client for your cw-mcp-server.

This module spawns your cw-mcp-server (Node/TypeScript, stdio transport)
as a subprocess and communicates via the Model Context Protocol.

Architecture:
  ┌──────────────┐   MCP (stdio)   ┌────────────────┐   HTTPS   ┌──────────┐
  │ Gone-Phishing │ ─────────────→  │ cw-mcp-server  │ ───────→  │ CW Cloud │
  │ (Python)      │   JSON-RPC      │ (Node, 73 tools)│          └──────────┘
  └──────────────┘                  └────────────────┘

Setup:
  1. Build cw-mcp-server:  cd /path/to/cw-mcp-server && npm run build
  2. Set CW_MCP_SERVER_DIR in .env to the cw-mcp-server directory
  3. Set CW environment variables (CW_COMPANY_ID, CW_PUBLIC_KEY, etc.)
  4. This module handles subprocess lifecycle automatically

The session is lazily initialised on first tool call and reused.
If the subprocess dies it is restarted on the next call.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from config import (
    CW_BASE_URL,
    CW_COMPANY_ID,
    CW_PRIVATE_KEY,
    CW_PUBLIC_KEY,
)

logger = logging.getLogger(__name__)

# Path to your built cw-mcp-server (must contain dist/index.js after `npm run build`)
CW_MCP_SERVER_DIR: str = os.getenv("CW_MCP_SERVER_DIR", "")
CW_CLIENT_ID: str = os.getenv("CW_CLIENT_ID", "")

# ---------------------------------------------------------------------------
# MCP client session (lazy singleton)
# ---------------------------------------------------------------------------

_session = None
_client_ctx = None
_session_ctx = None


async def _get_session():
    """Lazily initialise the MCP client session, spawning the cw-mcp-server subprocess."""
    global _session, _client_ctx, _session_ctx

    if _session is not None:
        return _session

    if not CW_MCP_SERVER_DIR:
        raise RuntimeError(
            "CW_MCP_SERVER_DIR not set. Point it at your cw-mcp-server directory "
            "(the one containing dist/index.js after `npm run build`)."
        )

    try:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
    except ImportError:
        raise RuntimeError(
            "MCP Python SDK not installed. Run: pip install mcp"
        )

    server_script = os.path.join(CW_MCP_SERVER_DIR, "dist", "index.js")
    if not os.path.isfile(server_script):
        raise RuntimeError(
            f"cw-mcp-server not found at {server_script}. "
            f"Run: cd {CW_MCP_SERVER_DIR} && npm run build"
        )

    server_params = StdioServerParameters(
        command="node",
        args=[server_script],
        env={
            **os.environ,
            "CW_COMPANY_ID": CW_COMPANY_ID,
            "CW_PUBLIC_KEY": CW_PUBLIC_KEY,
            "CW_PRIVATE_KEY": CW_PRIVATE_KEY,
            "CW_CLIENT_ID": CW_CLIENT_ID,
            "CW_SITE_URL": CW_BASE_URL,
        },
    )

    _client_ctx = stdio_client(server_params)
    read, write = await _client_ctx.__aenter__()

    _session_ctx = ClientSession(read, write)
    _session = await _session_ctx.__aenter__()
    await _session.initialize()

    tools = await _session.list_tools()
    logger.info("cw-mcp-server connected: %d tools available", len(tools.tools))

    return _session


async def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on the cw-mcp-server and return the result as a dict."""
    try:
        session = await _get_session()
        result = await session.call_tool(name, arguments)

        # MCP tool results are a list of content blocks
        texts = [block.text for block in result.content if hasattr(block, "text")]
        combined = "\n".join(texts)

        # Try to parse as JSON (the response-formatter in cw-mcp returns structured text)
        try:
            return {"success": True, "data": json.loads(combined)}
        except json.JSONDecodeError:
            return {"success": True, "data": combined}

    except RuntimeError as exc:
        # Config / setup errors — don't retry
        logger.warning("cw-mcp setup error: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        # Session died — reset so next call reconnects
        logger.exception("cw-mcp tool call failed: %s", name)
        await _close_session()
        return {"error": f"cw-mcp error: {exc}"}


async def _close_session() -> None:
    """Tear down the MCP session and subprocess."""
    global _session, _client_ctx, _session_ctx
    try:
        if _session_ctx:
            await _session_ctx.__aexit__(None, None, None)
        if _client_ctx:
            await _client_ctx.__aexit__(None, None, None)
    except Exception:
        pass
    _session = _client_ctx = _session_ctx = None


# ---------------------------------------------------------------------------
# Synchronous wrappers (FastAPI endpoints are async but tool callers may not be)
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
        # Already in an async context — just return the coroutine for await
        return coro
    except RuntimeError:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Public tool functions — IRP-relevant subset of the 73 tools
# ---------------------------------------------------------------------------

async def tool_create_ticket(
    summary: str,
    company_id: int,
    description: str = "",
    board_id: int | None = None,
    priority_id: int | None = None,
    owner_identifier: str | None = None,
) -> dict[str, Any]:
    """Create a CW Manage service ticket for incident tracking.

    Maps to cw_create_ticket on the MCP server.
    """
    args: dict[str, Any] = {
        "summary": summary,
        "company": {"id": company_id},
    }
    if description:
        args["initialDescription"] = description
    if board_id:
        args["board"] = {"id": board_id}
    if priority_id:
        args["priority"] = {"id": priority_id}
    if owner_identifier:
        args["owner"] = {"identifier": owner_identifier}

    return await _call_tool("cw_create_ticket", args)


async def tool_get_ticket(ticket_id: int) -> dict[str, Any]:
    """Retrieve a CW Manage ticket by ID."""
    return await _call_tool("cw_get_ticket", {"id": ticket_id})


async def tool_update_ticket(
    ticket_id: int,
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update a ticket via JSON Patch operations.

    Example operations:
      [{"op": "replace", "path": "/status/id", "value": 123}]
      [{"op": "replace", "path": "/priority/id", "value": 4}]
    """
    return await _call_tool("cw_update_ticket", {
        "id": ticket_id,
        "operations": operations,
    })


async def tool_add_ticket_note(
    ticket_id: int,
    text: str,
    internal: bool = True,
) -> dict[str, Any]:
    """Add a note to a ticket. internal=True for internal analysis notes."""
    return await _call_tool("cw_add_ticket_note", {
        "id": ticket_id,
        "text": text,
        "internalAnalysisFlag": internal,
    })


async def tool_list_tickets(
    conditions: str = "",
    limit: int = 25,
) -> dict[str, Any]:
    """Search CW tickets using ConnectWise conditions syntax.

    Examples:
      conditions='status/name="Open"'
      conditions='summary contains "ransomware"'
      conditions='company/id=7'
    """
    args: dict[str, Any] = {"limit": limit, "offset": 0}
    if conditions:
        args["conditions"] = conditions
    return await _call_tool("cw_list_tickets", args)


async def tool_list_ticket_notes(
    ticket_id: int,
    limit: int = 25,
) -> dict[str, Any]:
    """List notes on a ticket."""
    return await _call_tool("cw_list_ticket_notes", {
        "id": ticket_id,
        "limit": limit,
        "offset": 0,
    })


# -- Supporting lookups (for resolving IDs) ----------------------------------

async def tool_list_companies(
    conditions: str = "",
    limit: int = 25,
) -> dict[str, Any]:
    """List CW companies. Use to resolve company IDs for ticket creation."""
    args: dict[str, Any] = {"limit": limit, "offset": 0}
    if conditions:
        args["conditions"] = conditions
    return await _call_tool("cw_list_companies", args)


async def tool_list_boards(limit: int = 25) -> dict[str, Any]:
    """List service boards. Use to resolve board IDs."""
    return await _call_tool("cw_list_boards", {"limit": limit, "offset": 0})


async def tool_list_board_statuses(board_id: int) -> dict[str, Any]:
    """List valid statuses for a board. Use to resolve status IDs for updates."""
    return await _call_tool("cw_list_board_statuses", {"id": board_id, "limit": 100, "offset": 0})


async def tool_list_members(
    conditions: str = "",
    limit: int = 25,
) -> dict[str, Any]:
    """List system members. Use to resolve owner identifiers."""
    args: dict[str, Any] = {"limit": limit, "offset": 0}
    if conditions:
        args["conditions"] = conditions
    return await _call_tool("cw_list_members", args)
