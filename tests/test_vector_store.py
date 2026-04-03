"""Vector store tests — chunking logic and ingestion behavior.

These test the parts that, if broken, silently degrade search quality
without raising errors. Found out the hard way that bad chunk overlap
makes ransomware and phishing playbooks cross-contaminate each other.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from vector_store import chunk_document, ingest_playbooks, search_playbooks


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def test_chunk_basic():
    text = "a" * 1000
    chunks = chunk_document(text, size=500, overlap=100)
    assert len(chunks) == 3  # 0-500, 400-900, 800-1000


def test_chunk_short_text_returns_single_chunk():
    chunks = chunk_document("Short incident description.")
    assert len(chunks) == 1


def test_chunk_empty_string_returns_nothing():
    assert chunk_document("") == []
    assert chunk_document("   ") == []


def test_chunk_overlap_means_adjacent_chunks_share_content():
    """Overlap is the whole point — retrieval needs context at boundaries."""
    text = "A" * 200 + "B" * 200 + "C" * 200
    chunks = chunk_document(text, size=300, overlap=100)
    # The boundary between A and B should appear in multiple chunks
    assert any("A" in c and "B" in c for c in chunks)


def test_chunk_preserves_full_content():
    """Every character in the source should appear in at least one chunk."""
    text = "The quick brown fox jumps over the lazy dog. " * 50
    chunks = chunk_document(text, size=100, overlap=20)
    reconstructed = set()
    for chunk in chunks:
        for i, char in enumerate(chunk):
            reconstructed.add(char)
    for char in set(text.strip()):
        assert char in reconstructed


# ---------------------------------------------------------------------------
# Ingestion edge cases
# ---------------------------------------------------------------------------


def test_ingest_skips_empty_files(tmp_path):
    """A .md file with only whitespace should not produce chunks."""
    (tmp_path / "empty.md").write_text("   \n\n  ")
    (tmp_path / "real.md").write_text("# Phishing\n\nDon't click suspicious links.")
    result = ingest_playbooks(str(tmp_path))
    assert result["files_ingested"] == 1
    assert result["details"][0]["file"] == "real.md"


def test_ingest_skips_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Do not ingest me")
    (tmp_path / "test-playbook.md").write_text("# Actual playbook content here")
    result = ingest_playbooks(str(tmp_path))
    files = [d["file"] for d in result["details"]]
    assert "README.md" not in files
    assert "test-playbook.md" in files


# ---------------------------------------------------------------------------
# Search quality
# ---------------------------------------------------------------------------


def test_search_returns_content_not_just_ids(ingested_playbooks):
    results = search_playbooks("ransomware attack encrypted files")
    assert len(results) > 0
    for r in results:
        assert "content" in r
        assert len(r["content"]) > 10  # actual text, not empty
        assert "metadata" in r
        assert "playbook_type" in r["metadata"]


def test_search_distance_increases_with_irrelevance(ingested_playbooks):
    """More relevant queries should have lower distance scores."""
    relevant = search_playbooks("ransomware encrypted files bitcoin ransom", n_results=1)
    irrelevant = search_playbooks("best pizza restaurants in downtown chicago", n_results=1)
    # Lower distance = more relevant
    assert relevant[0]["distance"] < irrelevant[0]["distance"]
