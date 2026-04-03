#!/bin/sh
set -e

echo "═══ Gone-Phishing — starting ═══"

cd /app/server

echo "Validating configuration..."
python -c "from config import validate; validate()"

echo "Ingesting playbooks..."
python -c "
from vector_store import ingest_playbooks
r = ingest_playbooks()
print(f'  {r[\"files_ingested\"]} files, {r[\"total_chunks\"]} chunks indexed')
"

echo "Starting server on port ${PORT:-8100}..."
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8100}"
