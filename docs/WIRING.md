# Wiring Guide

Step-by-step instructions for connecting every external dependency.

---

## Chat UI Options

Gone-Phishing ships with a built-in single-file web UI (`web/index.html`). You can swap it for a more capable chat engine by setting `CHAT_UI` in `.env`.

### Option 1: Built-in (default)

Zero dependencies. A single-page dark-theme chat interface served directly by FastAPI.

```bash
CHAT_UI=builtin   # or just don't set it
cd server && python app.py
# → http://localhost:8100
```

Good for demos, air-gapped environments, and keeping the dependency tree minimal.

---

### Option 2: Chainlit

[Chainlit](https://github.com/Chainlit/chainlit) (Apache 2.0, 9k+ stars) mounts directly into your FastAPI process — no separate server, no Docker, no JavaScript build step. It gives you streaming responses, step visualisation, file upload, auth (OAuth / header), and a polished React frontend out of the box.

**Why it's a good fit:** The IRP engine already runs FastAPI. Chainlit plugs in with one function call (`mount_chainlit`), inherits your existing endpoints, and adds a production-grade chat UI at `/chat`.

```bash
pip install chainlit>=2.10.0
```

```bash
# .env
CHAT_UI=chainlit
```

```bash
cd server && python app.py
# API   → http://localhost:8100/api/*
# Chat  → http://localhost:8100/chat
```

The Chainlit integration lives in `server/cl_app.py`. Customise it to add step indicators for each IRP phase (Identification → Containment → Eradication → Recovery).

---

## ConnectWise MCP

The CW integration (`server/tools/cw_tools.py`) is an MCP client that spawns your **cw-mcp-server** (73-tool TypeScript MCP server) as a subprocess and communicates via stdio JSON-RPC.

### Architecture

```
┌──────────────┐   MCP (stdio)   ┌────────────────┐   HTTPS   ┌──────────┐
│ Gone-Phishing │ ─────────────→  │ cw-mcp-server  │ ───────→  │ CW Cloud │
│ (Python)      │   JSON-RPC      │ (Node, 73 tools)│          └──────────┘
└──────────────┘                  └────────────────┘
```

Gone-Phishing spawns the Node process, establishes an MCP session, and calls tools like `cw_create_ticket` and `cw_add_ticket_note` through the protocol. The session is lazily initialised on first tool call and automatically reconnects if the subprocess dies.

### Setup

```bash
# 1. Install the MCP Python SDK
pip install mcp

# 2. Build cw-mcp-server
cd /path/to/cw-mcp-server
npm install && npm run build    # produces dist/index.js

# 3. Set env vars in .env
CW_MCP_SERVER_DIR=/absolute/path/to/cw-mcp-server
CW_COMPANY_ID=yourcompany
CW_PUBLIC_KEY=your_public_key
CW_PRIVATE_KEY=your_private_key
CW_CLIENT_ID=your_client_id
CW_BASE_URL=https://api-na.myconnectwise.net
```

### IRP-relevant tools exposed

`cw_tools.py` wraps these tools from the 73-tool MCP server:

| Python function              | MCP tool                 | Purpose                          |
| ---------------------------- | ------------------------ | -------------------------------- |
| `tool_create_ticket()`       | `cw_create_ticket`       | Create incident ticket           |
| `tool_get_ticket()`          | `cw_get_ticket`          | Look up ticket by ID             |
| `tool_update_ticket()`       | `cw_update_ticket`       | Update via JSON Patch            |
| `tool_add_ticket_note()`     | `cw_add_ticket_note`     | Add internal/external notes      |
| `tool_list_tickets()`        | `cw_list_tickets`        | Search with CW conditions syntax |
| `tool_list_ticket_notes()`   | `cw_list_ticket_notes`   | List notes on a ticket           |
| `tool_list_companies()`      | `cw_list_companies`      | Resolve company IDs              |
| `tool_list_boards()`         | `cw_list_boards`         | Resolve board IDs                |
| `tool_list_board_statuses()` | `cw_list_board_statuses` | Valid statuses for a board       |
| `tool_list_members()`        | `cw_list_members`        | Resolve owner identifiers        |

All 73 tools remain available if you need to extend beyond this subset — just add more wrapper functions following the same `_call_tool()` pattern.

### Graceful degradation

If `CW_MCP_SERVER_DIR` is not set or the server can't start, every tool function returns an error dict. The IRP engine stays fully operational — you just won't get CW ticket integration.

### For Railway deployment

If you want CW integration in production, you have two options:

1. **Bundle cw-mcp-server into the Docker image** — add a build step that installs Node and runs `npm install && npm run build` inside the container
2. **Run cw-mcp-server separately** and switch `cw_tools.py` to use SSE transport instead of stdio (the MCP SDK supports both)

---

## N8N Webhooks

The N8N integration (`server/tools/n8n_tools.py`) fires webhooks into your N8N instance for:

- **Escalation chains** — email / Teams / Slack fan-out
- **Evidence snapshots** — kick off RMM scripts to preserve logs
- **Notifications** — route alerts by channel type

### Setup

1. Import or build the matching workflows in your N8N instance.
2. Each workflow should expose a webhook trigger node at these paths:

   | Webhook path      | Purpose                      |
   | ----------------- | ---------------------------- |
   | `/irp-escalation` | Severity-based alert fan-out |
   | `/irp-evidence`   | RMM evidence collection      |
   | `/irp-notify`     | General notification routing |

3. Set `N8N_BASE_URL` in `.env`. Optionally set `N8N_WEBHOOK_SECRET` if your workflows validate it.

---

## LLM Providers

Set `LLM_PROVIDER` and `LLM_MODEL` in `.env`.

| Provider    | Required env var    | Example model              |
| ----------- | ------------------- | -------------------------- |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| `openai`    | `OPENAI_API_KEY`    | `gpt-4o`                   |
| `gemini`    | `GOOGLE_API_KEY`    | `gemini-1.5-pro`           |
| `ollama`    | `OLLAMA_BASE_URL`   | Set via `OLLAMA_MODEL`     |

For Ollama, make sure `ollama serve` is running and you've pulled the model:

```bash
ollama pull llama3.1:8b
```

---

## Railway Deployment

Gone-Phishing ships with a `Dockerfile`, `railway.json`, and `start.sh` ready for one-command Railway deployment.

### Prerequisites

- [Railway CLI](https://docs.railway.com/guides/cli) installed and authenticated
- A Railway account (free tier works for demos)

### Deploy

```bash
# From the repo root
railway init          # Create a new Railway project
railway up            # Build and deploy
```

Or connect via GitHub:

1. Push the repo to GitHub
2. In Railway dashboard → **New Project** → **Deploy from GitHub repo**
3. Select the repo — Railway detects the Dockerfile automatically

### Environment variables

Set these in the Railway dashboard under your service's **Variables** tab:

| Variable            | Required | Example                    |
| ------------------- | -------- | -------------------------- |
| `ANTHROPIC_API_KEY` | Yes\*    | `sk-ant-...`               |
| `LLM_PROVIDER`      | No       | `anthropic` (default)      |
| `LLM_MODEL`         | No       | `claude-sonnet-4-20250514` |
| `CHAT_UI`           | No       | `builtin` (default)        |

\*Required for default config. Set your chosen provider's key instead if using OpenAI/Gemini.

Railway auto-injects `PORT` — the app binds to it automatically.

### Health check

Railway hits `GET /api/health` to verify the service is up. This is configured in `railway.json`.

### Custom domain

```bash
railway domain
# → assigns a *.up.railway.app subdomain

# Or in the dashboard: Settings → Networking → Custom Domain
# Point your DNS CNAME to the Railway domain
```

### What happens on deploy

1. Docker builds the image (~60s first time, cached after)
2. `start.sh` runs: ingests playbooks into ChromaDB, then starts uvicorn
3. Health check passes → service goes live
4. Railway assigns a public URL

### Estimated cost

Railway's free tier gives you $5/month in credits. This app idles at ~256MB RAM and near-zero CPU. Typical demo usage stays well within free tier. If you need always-on, the Hobby plan ($5/mo) covers it.

### Gotcha: ChromaDB persistence

Railway containers are ephemeral — if the container restarts, ChromaDB re-indexes from the playbook files (takes ~2 seconds on startup). This is fine because the playbooks are checked into the repo. If you later want persistent vector storage across deploys, attach a Railway Volume mounted at `/app/data/chroma`.
