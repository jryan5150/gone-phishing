"""
Vector store — ChromaDB ingestion and semantic search over IRP playbooks.

Chunk strategy: ~500-char windows with 100-char overlap.
Embedding: ChromaDB default (all-MiniLM-L6-v2 via sentence-transformers).
"""

from __future__ import annotations

import glob
import os
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from config import CHROMA_DIR, PLAYBOOKS_DIR

COLLECTION_NAME = "irp_playbooks"

_embedding_fn = embedding_functions.DefaultEmbeddingFunction()


def _get_client() -> chromadb.PersistentClient:
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _get_collection(client: chromadb.PersistentClient) -> Any:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_document(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    """Split *text* into overlapping windows of roughly *size* characters."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        window = text[start : start + size].strip()
        if window:
            chunks.append(window)
        start += size - overlap
    return chunks


def ingest_playbooks(playbooks_dir: str | None = None) -> dict[str, Any]:
    """(Re-)ingest every .md file under *playbooks_dir* into ChromaDB.

    Returns a summary dict with ``files_ingested``, ``total_chunks``, and ``details``.
    """
    src = playbooks_dir or str(PLAYBOOKS_DIR)
    client = _get_client()
    collection = _get_collection(client)

    # Wipe existing data for a clean re-index.
    try:
        ids = collection.get()["ids"]
        if ids:
            collection.delete(ids=ids)
    except Exception:
        pass

    md_files = sorted(glob.glob(os.path.join(src, "*.md")))
    total_chunks = 0
    details: list[dict[str, Any]] = []

    for filepath in md_files:
        filename = os.path.basename(filepath)
        if filename in ("README.md", "full-irp-template.md"):
            continue

        with open(filepath) as f:
            content = f.read()
        if not content.strip():
            continue

        playbook_type = filename.removesuffix(".md")
        chunks = chunk_document(content)

        ids = [f"{playbook_type}__chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source_file": filename,
                "playbook_type": playbook_type,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        collection.add(ids=ids, documents=chunks, metadatas=metadatas)
        total_chunks += len(chunks)
        details.append({"file": filename, "chunks": len(chunks)})

    return {
        "files_ingested": len(details),
        "total_chunks": total_chunks,
        "details": details,
    }


def search_playbooks(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Semantic search — returns the *n_results* closest playbook chunks."""
    client = _get_client()
    collection = _get_collection(client)

    results = collection.query(query_texts=[query], n_results=n_results)

    matches: list[dict[str, Any]] = []
    for i in range(len(results["ids"][0])):
        matches.append(
            {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
        )
    return matches


def list_playbooks() -> list[dict[str, Any]]:
    """Return de-duplicated metadata for every ingested playbook type."""
    client = _get_client()
    collection = _get_collection(client)

    seen: dict[str, dict[str, Any]] = {}
    for meta in collection.get()["metadatas"]:
        ptype = meta["playbook_type"]
        if ptype not in seen:
            seen[ptype] = {
                "playbook_type": ptype,
                "source_file": meta["source_file"],
                "total_chunks": meta["total_chunks"],
            }
    return list(seen.values())
