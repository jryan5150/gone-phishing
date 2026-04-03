"""
Chainlit chat application — mounted by app.py when CHAT_UI=chainlit.

This file is the Chainlit "target" passed to mount_chainlit().
It wires Chainlit's event hooks to the IRP engine's core functions.
"""

from __future__ import annotations

import chainlit as cl

from llm import chat_response, generate_action_plan
from vector_store import search_playbooks


@cl.on_chat_start
async def on_start() -> None:
    cl.user_session.set("history", [])
    await cl.Message(
        content=(
            "**Gone-Phishing IRP Assistant** — NIST 800-61 aligned.\n\n"
            "Describe a security incident and I'll generate an actionable response plan "
            "with role assignments, timelines, and regulatory notifications.\n\n"
            "Try: *A user reported they clicked a link in a suspicious email "
            "and entered their Microsoft 365 credentials on a spoofed login page.*"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    history: list[dict] = cl.user_session.get("history", [])

    if not history:
        # First message → full incident analysis
        matches = search_playbooks(message.content, n_results=8)
        if not matches:
            await cl.Message(content="No playbooks ingested. Run `POST /api/ingest` first.").send()
            return

        plan = generate_action_plan(
            incident_description=message.content,
            playbook_context=matches,
        )
        history.append({"role": "user", "content": message.content})
        history.append({"role": "assistant", "content": plan})
        cl.user_session.set("history", history)
        await cl.Message(content=plan).send()
    else:
        # Follow-up → chat with context
        history.append({"role": "user", "content": message.content})
        matches = search_playbooks(message.content, n_results=5)
        response = chat_response(messages=history, playbook_context=matches or None)
        history.append({"role": "assistant", "content": response})
        cl.user_session.set("history", history)
        await cl.Message(content=response).send()
