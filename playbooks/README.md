# Playbooks

Drop `.md` files here — they get auto-ingested into ChromaDB on `POST /api/ingest` or server restart.

## How it works

1. Save an incident response procedure as a Markdown file in this directory
2. Hit `/api/ingest` (or restart the server)
3. The system chunks the doc (~500 char windows, 100 char overlap), embeds it, and makes it searchable

## Naming

Use kebab-case: `ransomware.md`, `insider-threat.md`, `ddos-response.md`

## Template

Each playbook should cover: scenario description, severity indicators, immediate actions (first 15–60 min), containment steps, investigation checklist, recovery steps, notification requirements, evidence preservation.

## Notes

- `full-irp-template.md` is the master reference and is **not** ingested (too large for clean chunking)
- `README.md` is also excluded from ingestion
- Shorter, focused docs produce better retrieval than monoliths
