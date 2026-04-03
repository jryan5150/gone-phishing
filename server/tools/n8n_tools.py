"""
N8N webhook tools — trigger automation workflows from the IRP engine.

Each function fires a webhook and returns immediately.  The N8N workflow
handles the actual fan-out (email, Teams, Slack, RMM, evidence collection).

Wire-up:
  1. Import the matching workflow JSON into your N8N instance
  2. Set N8N_BASE_URL in .env
  3. See docs/WIRING.md → "N8N Webhooks" for workflow templates

All functions are fire-and-forget: they return status stubs until the
corresponding N8N workflows are built.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import N8N_BASE_URL, N8N_WEBHOOK_SECRET

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_DEFAULT_URL = "http://localhost:5678"


def is_configured() -> bool:
    """True if N8N_BASE_URL has been set to something other than the default."""
    return bool(N8N_BASE_URL) and N8N_BASE_URL != _DEFAULT_URL


def _fire_webhook(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not is_configured():
        return {"status": "not_configured", "error": "N8N_BASE_URL not set"}

    url = f"{N8N_BASE_URL.rstrip('/')}/webhook/{path}"
    headers = {}
    if N8N_WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = N8N_WEBHOOK_SECRET

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return {"status": "triggered", "webhook": url}
    except httpx.ConnectError:
        msg = f"N8N unreachable at {N8N_BASE_URL} — is the instance running?"
        logger.warning(msg)
        return {"status": "unavailable", "error": msg}
    except Exception as exc:
        logger.exception("N8N webhook error")
        return {"status": "error", "error": str(exc)}


def tool_trigger_escalation(
    incident_id: str,
    severity: str,
    summary: str,
    assigned_to: str = "",
) -> dict[str, Any]:
    """Fire the escalation chain (email / Teams / Slack fan-out)."""
    return _fire_webhook(
        "irp-escalation",
        {
            "incident_id": incident_id,
            "severity": severity,
            "summary": summary,
            "assigned_to": assigned_to,
        },
    )


def tool_trigger_evidence_snapshot(
    incident_id: str,
    target_systems: list[str],
) -> dict[str, Any]:
    """Kick off automated evidence preservation via RMM scripts."""
    return _fire_webhook(
        "irp-evidence",
        {"incident_id": incident_id, "target_systems": target_systems},
    )


def tool_trigger_notification(
    recipients: list[str],
    subject: str,
    body: str,
    channel: str = "email",
) -> dict[str, Any]:
    """Send a notification through a configured channel."""
    return _fire_webhook(
        "irp-notify",
        {
            "recipients": recipients,
            "subject": subject,
            "body": body,
            "channel": channel,
        },
    )
