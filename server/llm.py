"""
LLM orchestration — action plan generation and conversational follow-up.

Uses the adapter layer so the provider is determined by LLM_PROVIDER in .env.
"""

from __future__ import annotations

from adapters import LLMAdapter, get_adapter

SYSTEM_PROMPT = """\
You are an Incident Response Assistant for a Managed Service Provider (MSP).
Your job is to help IT teams quickly identify the correct incident response
playbook and generate actionable, role-assigned checklists they can execute
immediately during a security incident.

You have access to NIST SP 800-61 aligned incident response playbooks covering:
• Ransomware, Phishing, Data Breaches, Business Email Compromise (BEC)
• Response phases: Preparation → Identification → Containment → Eradication → Recovery → Lessons Learned
• Severity classification: Critical (S1), High (S2), Medium (S3), Low (S4)
• Communication plans (internal + external) and regulatory notification requirements

When given an incident description:
1. Classify the scenario type and severity
2. Map it to the relevant playbook
3. Generate a prioritised action checklist with:
   - Step numbering and time estimates per phase
   - Role assignments (IR Lead, IT Security, SysAdmin, Legal, Comms, etc.)
   - Immediate actions separated from follow-up actions
4. Flag regulatory notification requirements

Be direct, concise, and actionable.  This runs during live incidents — no filler.
Format output in clean Markdown with headers and checkboxes (- [ ])."""


def _build_context(playbook_chunks: list[dict]) -> str:
    """Flatten retrieved playbook chunks into a single context block."""
    return "\n\n---\n\n".join(
        f"[Source: {c['metadata']['playbook_type']}]\n{c['content']}"
        for c in playbook_chunks
    )


def generate_action_plan(
    incident_description: str,
    playbook_context: list[dict],
    severity: str | None = None,
    affected_systems: str | None = None,
    adapter: LLMAdapter | None = None,
) -> str:
    """Generate a role-assigned action plan from an incident description."""
    llm = adapter or get_adapter()
    context = _build_context(playbook_context)

    prompt = f"## Incident Report\n\n**Description:** {incident_description}\n"
    if severity:
        prompt += f"**Assessed Severity:** {severity}\n"
    if affected_systems:
        prompt += f"**Affected Systems:** {affected_systems}\n"

    prompt += f"""
## Retrieved Playbook Context

{context}

---

Based on the incident and the playbook content above, generate:
1. **Scenario Classification** — incident type + severity level
2. **Immediate Action Checklist** (first 15–60 min) with role assignments
3. **Containment & Investigation Checklist** with role assignments
4. **Recovery Checklist**
5. **Notification Requirements** — who, when, method
6. **Evidence Preservation Notes** — what to capture before it's lost

Use checkbox format (- [ ]) with bold role prefixes for every action item."""

    return llm.complete(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )


def chat_response(
    messages: list[dict[str, str]],
    playbook_context: list[dict] | None = None,
    adapter: LLMAdapter | None = None,
) -> str:
    """General follow-up chat with optional playbook context injected."""
    llm = adapter or get_adapter()

    system = SYSTEM_PROMPT
    if playbook_context:
        system += f"\n\n## Available Playbook Context\n\n{_build_context(playbook_context)}"

    return llm.complete(system=system, messages=messages)
