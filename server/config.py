"""
Configuration — single source of truth.

Every tunable reads from env (with .env fallback via python-dotenv).
Import settings from here; never call os.getenv() elsewhere.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# -- Paths ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
PLAYBOOKS_DIR = Path(os.getenv("PLAYBOOKS_DIR", str(BASE_DIR / "playbooks")))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", str(BASE_DIR / "data" / "chroma")))

# -- Server -----------------------------------------------------------------
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8100"))

# -- LLM (BYOM) ------------------------------------------------------------
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# -- ConnectWise MCP --------------------------------------------------------
CW_MCP_SERVER_DIR: str = os.getenv("CW_MCP_SERVER_DIR", "")
CW_CLIENT_ID: str = os.getenv("CW_CLIENT_ID", "")
CW_COMPANY_ID: str = os.getenv("CW_COMPANY_ID", "")
CW_PUBLIC_KEY: str = os.getenv("CW_PUBLIC_KEY", "")
CW_PRIVATE_KEY: str = os.getenv("CW_PRIVATE_KEY", "")
CW_BASE_URL: str = os.getenv("CW_BASE_URL", "https://api-na.myconnectwise.net")

# -- N8N --------------------------------------------------------------------
N8N_BASE_URL: str = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_WEBHOOK_SECRET: str = os.getenv("N8N_WEBHOOK_SECRET", "")

# -- Chat UI ----------------------------------------------------------------
CHAT_UI: str = os.getenv("CHAT_UI", "builtin")

# -- Tool registry ----------------------------------------------------------
ENABLED_TOOLS: list[str] = os.getenv("ENABLED_TOOLS", "irp,cw,n8n").split(",")

# -- Startup validation -----------------------------------------------------
_PROVIDER_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}


def validate() -> None:
    """Check required config at startup. Logs warnings, exits on fatal errors."""
    required_key = _PROVIDER_KEYS.get(LLM_PROVIDER)
    if required_key and not os.getenv(required_key):
        logger.error(
            "LLM_PROVIDER=%s but %s is not set. "
            "Set it in .env or switch providers.",
            LLM_PROVIDER,
            required_key,
        )
        sys.exit(1)

    if LLM_PROVIDER == "ollama":
        logger.info("LLM_PROVIDER=ollama — ensure 'ollama serve' is running at %s", OLLAMA_BASE_URL)

    if not PLAYBOOKS_DIR.exists():
        logger.warning("PLAYBOOKS_DIR %s does not exist", PLAYBOOKS_DIR)
