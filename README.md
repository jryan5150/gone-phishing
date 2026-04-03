# Gone-Phishing

AI-powered Incident Response Plan engine for MSPs. Takes a free-text incident description, matches it against NIST 800-61 aligned playbooks via semantic search, and generates a role-assigned, time-bound action plan with regulatory notification requirements.

## What it does

```
incident description  →  ChromaDB semantic search  →  LLM action plan
                          (playbook matching)          (role-assigned checklist)
```

1. Ingests IRP playbooks (Markdown files) into ChromaDB as embeddings
2. Semantically matches an incident description to the right playbook
3. Generates a prioritised action checklist with role assignments, timelines, and regulatory flags
4. Provides follow-up chat for investigation questions

## Stack

| Layer        | Technology                                          |
| ------------ | --------------------------------------------------- |
| API          | FastAPI (Python)                                    |
| Vector store | ChromaDB (cosine similarity, sentence-transformers) |
| LLM          | BYOM — Anthropic, OpenAI, Gemini, or Ollama         |
| Chat UI      | Built-in, Chainlit, or Open WebUI                   |
| Integrations | ConnectWise Manage (via cw-mcp), N8N webhooks       |

## Quick start

```bash
git clone https://github.com/lexcom-systems/gone-phishing.git
cd gone-phishing

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY (or your chosen provider)

# Run
cd server
python app.py
# → http://localhost:8100
```

The server auto-ingests playbooks on startup.

## Project structure

```
gone-phishing/
├── server/
│   ├── app.py                 # FastAPI server + chat UI mounting
│   ├── config.py              # Centralised config with startup validation
│   ├── vector_store.py        # ChromaDB ingestion + semantic search
│   ├── llm.py                 # Action plan generation (provider-agnostic)
│   ├── cl_app.py              # Chainlit integration (optional)
│   │
│   ├── adapters/              # BYOM — Bring Your Own Model
│   │   ├── base.py            # Abstract adapter interface
│   │   ├── anthropic_adapter.py
│   │   ├── openai_adapter.py
│   │   ├── gemini_adapter.py
│   │   └── ollama_adapter.py
│   │
│   └── tools/                 # MCP tool modules
│       ├── irp_tools.py       # Core IRP (search, plan, list)
│       ├── cw_tools.py        # ConnectWise Manage (via cw-mcp)
│       └── n8n_tools.py       # N8N webhook triggers
│
├── tests/                     # 60 tests — API, integration, data, adapters
│   ├── conftest.py            # Shared fixtures (temp ChromaDB, TestClient)
│   ├── test_api.py            # Endpoint contracts + validation
│   ├── test_integration.py    # Full lifecycle, error handling, concurrency
│   ├── test_vector_store.py   # Chunking, search quality, ingestion
│   ├── test_adapters.py       # BYOM registry, ABC enforcement
│   └── test_scenarios.py      # Corpus integrity + generator reproducibility
│
├── scripts/
│   └── generate_scenarios.py  # Procedural scenario generator (pure Python)
│
├── playbooks/                 # Drop .md files here → auto-ingested
│   ├── ransomware.md
│   ├── phishing.md
│   ├── data-breach.md
│   ├── bec.md
│   └── ...                    # 11 total (severity, comms, regulatory, etc.)
│
├── web/
│   └── index.html             # Built-in chat UI (marked.js for rendering)
│
├── data/
│   ├── scenarios.json         # 2,000 generated incident scenarios
│   └── chroma/                # ChromaDB persistence (.gitignored)
│
├── docs/
│   └── WIRING.md              # Setup guide: chat UIs, CW MCP, N8N, LLM providers
│
├── pyproject.toml
├── .env.example
├── .gitignore
└── requirements.txt
```

## API

| Endpoint         | Method | Description                         |
| ---------------- | ------ | ----------------------------------- |
| `/api/incident`  | POST   | Submit incident → get action plan   |
| `/api/chat`      | POST   | Follow-up questions in chat context |
| `/api/search`    | POST   | Direct playbook semantic search     |
| `/api/playbooks` | GET    | List all ingested playbooks         |
| `/api/ingest`    | POST   | Re-ingest playbook files            |
| `/api/health`    | GET    | Server health check                 |

## BYOM — Bring Your Own Model

Set `LLM_PROVIDER` in `.env`:

```bash
LLM_PROVIDER=anthropic      # Claude (default)
LLM_PROVIDER=openai          # GPT-4o
LLM_PROVIDER=gemini           # Gemini 1.5 Pro
LLM_PROVIDER=ollama            # Local models (Llama 3.1, Phi-3, etc.)
```

For Ollama, pull your model first: `ollama pull llama3.1:8b`

## Chat UI options

| Option     | Set `CHAT_UI=` | Install                | What you get                                        |
| ---------- | -------------- | ---------------------- | --------------------------------------------------- |
| Built-in   | `builtin`      | Nothing extra          | Single-file dark theme UI at `/`                    |
| Chainlit   | `chainlit`     | `pip install chainlit` | Production chat UI at `/chat` (mounts into FastAPI) |
| Open WebUI | —              | Docker container       | Full AI platform (connects via API)                 |
| Gradio     | —              | `pip install gradio`   | Quick demo interface                                |

See [docs/WIRING.md](docs/WIRING.md) for step-by-step setup instructions for each.

## Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

**60 tests** across 5 test modules:

| Module                 | Tests | What it covers                                                               |
| ---------------------- | ----- | ---------------------------------------------------------------------------- |
| `test_api.py`          | 23    | Endpoint contracts, validation, search ranking, idempotent ingestion         |
| `test_integration.py`  | 8     | Full request lifecycle, context passing, re-ingest safety, error propagation |
| `test_vector_store.py` | 9     | Chunking logic, overlap correctness, search quality, skip rules              |
| `test_adapters.py`     | 5     | BYOM registry, unknown provider rejection, ABC enforcement                   |
| `test_scenarios.py`    | 15    | Corpus integrity, distribution, MITRE coverage, generator reproducibility    |

Key things the tests verify:

- **Search ranking**: ransomware query → ransomware playbook first (not phishing)
- **Multi-turn chat**: search context uses latest user message, not first
- **Idempotent ingest**: re-ingestion produces identical chunk counts
- **Error propagation**: broken LLM → clean 500 with message, not stack trace
- **Data integrity**: all search results have metadata, no empty content
- **Generator determinism**: same seed → identical output

## Scenario corpus

`data/scenarios.json` contains 2,000 procedurally generated incident scenarios across 10 categories, seeded from MITRE ATT&CK techniques, real-world breach patterns, and MSP-specific environments.

Regenerate with:

```bash
python scripts/generate_scenarios.py --seed 42 --output data/scenarios.json
```

Use for:

- Tabletop exercises
- LLM fine-tuning / eval datasets
- Playbook gap analysis (which categories lack coverage?)
- Demo / sales presentations

## Adding playbooks

Drop any `.md` file into `playbooks/` and hit `POST /api/ingest`. The system chunks it, embeds it, and makes it searchable.

## ConnectWise + N8N integration

The IRP engine delegates to your existing **cw-mcp** server for ticket operations and fires webhooks to **N8N** for escalation chains. Neither is required — the engine runs standalone.

See [docs/WIRING.md](docs/WIRING.md) for full wiring instructions.

## Development Timeline

Built through AI-orchestrated development — brainstormed and prototyped on mobile, then moved to desktop for parallel agent execution and full orchestration. Each phase below links to its commit.

| Phase                       | What                                                                                                                                                    | Commit                            |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| **Foundation**              | IRP engine, BYOM adapters, CW MCP client, playbook ingestion, chat UI                                                                                   | [`283e870`](../../commit/283e870) |
| **Code Quality Audit**      | Fixed config duplication, removed dead code, singleton ChromaDB client, consistent pathlib                                                              | [`39d9ec9`](../../commit/39d9ec9) |
| **Operational Hardening**   | Startup config validation (fail fast on missing keys), real health check with dependency verification, CORS spec compliance                             | [`5efcb04`](../../commit/5efcb04) |
| **Adapter Instrumentation** | Logging on all LLM calls (model, latency, tokens), fixed Gemini SDK bug (system_instruction was in wrong location)                                      | [`3581961`](../../commit/3581961) |
| **Frontend Security**       | Replaced regex markdown with marked.js, added DOMPurify to prevent XSS via LLM prompt injection                                                         | [`7486c92`](../../commit/7486c92) |
| **Documentation Cleanup**   | Proper attribution for IRP template source, stripped leaked section numbers, removed docs for non-existent features                                     | [`5b45e3a`](../../commit/5b45e3a) |
| **Data Provenance**         | Procedural scenario generator (pure Python, seeded, 10 categories, MITRE ATT&CK, 20 ransomware variants) — data now has a generator, not a mystery blob | [`520b2b5`](../../commit/520b2b5) |
| **Test Suite**              | 60 tests: API contracts, integration lifecycle, search ranking quality, adapter registry, corpus integrity, generator determinism                       | [`fbc3834`](../../commit/fbc3834) |
| **Project Structure**       | pyproject.toml, proper package layout, README with test documentation, free-tier LLM guidance                                                           | [`35797cc`](../../commit/35797cc) |
| **Security Review**         | Rate limiting (slowapi), security headers, generic error messages (no internal detail leakage), XSS prevention                                          | _this commit_                     |

### Process

1. **Brainstorm + prototype** (mobile) — sketched the architecture, identified the playbook-to-vector-search pipeline, chose BYOM adapter pattern
2. **Quality audit** (desktop) — systematic review of every file, identified 22 specific issues, prioritized by impact
3. **Parallel execution** — launched scenario generator as a background agent while fixing code quality, config validation, and health checks in the main session
4. **Security review** — invoked specialized security analysis that caught XSS-via-prompt-injection, error message leakage, and missing rate limiting before ship
5. **Test-driven validation** — wrote tests that verify _behavior_ (does ransomware query rank ransomware playbook first?) not just _syntax_ (does this function return a dict?)

## License

Lexcom Systems Group — internal tool.
