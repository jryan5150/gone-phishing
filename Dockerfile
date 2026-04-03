# ══════════════════════════════════════════════════════════════════════
# Gone-Phishing — Production container
# ══════════════════════════════════════════════════════════════════════
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for chromadb (sqlite3, build tools for native extensions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Dependencies (cached layer — only rebuilds when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .
RUN mkdir -p /app/data/chroma && chmod +x /app/start.sh

EXPOSE ${PORT:-8100}

CMD ["/app/start.sh"]
