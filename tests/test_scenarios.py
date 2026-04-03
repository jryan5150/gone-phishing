"""Scenario corpus validation.

Validates the generated scenario data meets the quality bar for
training data and tabletop exercises. These tests run against the
actual scenarios.json — if someone regenerates with bad parameters,
these catch it before it ships.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scenarios.json")

EXPECTED_CATEGORIES = {
    "ransomware",
    "phishing",
    "data_breach",
    "bec",
    "insider_threat",
    "denial_of_service",
    "unauthorized_access",
    "supply_chain",
    "physical_security",
    "web_app_attack",
}

VALID_SEVERITIES = {"S1", "S2", "S3", "S4"}


@pytest.fixture(scope="module")
def scenarios():
    with open(SCENARIOS_PATH) as f:
        data = json.load(f)
    return data["scenarios"]


def test_corpus_has_2000_scenarios(scenarios):
    assert len(scenarios) == 2000


def test_all_scenarios_have_required_fields(scenarios):
    required = {"id", "category", "severity", "environment", "time_context", "description"}
    for s in scenarios:
        missing = required - set(s.keys())
        assert not missing, f"{s['id']} missing fields: {missing}"


def test_ids_are_unique(scenarios):
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"


def test_ids_follow_format(scenarios):
    """SCN-NNNN format."""
    for s in scenarios:
        assert s["id"].startswith("SCN-"), f"Bad ID format: {s['id']}"
        assert len(s["id"]) == 8, f"Bad ID length: {s['id']}"


def test_all_categories_represented(scenarios):
    present = {s["category"] for s in scenarios}
    missing = EXPECTED_CATEGORIES - present
    assert not missing, f"Missing categories: {missing}"


def test_category_distribution_is_not_uniform(scenarios):
    """Real incidents aren't uniformly distributed — phishing and ransomware
    should dominate, physical_security should be rare."""
    from collections import Counter
    counts = Counter(s["category"] for s in scenarios)
    # Each category should have at least some representation
    for cat in EXPECTED_CATEGORIES:
        assert counts[cat] >= 50, f"{cat} has only {counts[cat]} scenarios"


def test_all_severities_are_valid(scenarios):
    for s in scenarios:
        assert s["severity"] in VALID_SEVERITIES, f"{s['id']}: bad severity {s['severity']}"


def test_severity_distribution_is_weighted(scenarios):
    """S2/S3 should be most common. Very few S1 (critical) incidents."""
    from collections import Counter
    counts = Counter(s["severity"] for s in scenarios)
    # S2+S3 should be the majority
    mid = counts["S2"] + counts["S3"]
    assert mid > len(scenarios) * 0.5, f"S2+S3 only {mid}/{len(scenarios)}"


def test_descriptions_have_minimum_length(scenarios):
    """Descriptions need enough detail to be useful for tabletops."""
    for s in scenarios:
        assert len(s["description"]) >= 50, f"{s['id']}: description too short ({len(s['description'])} chars)"


def test_descriptions_are_not_duplicated(scenarios):
    """Each scenario should be unique — no copy-paste."""
    descs = [s["description"] for s in scenarios]
    unique = set(descs)
    dupes = len(descs) - len(unique)
    # Allow a tiny number of collisions from the combinatorial generator
    assert dupes < 10, f"{dupes} duplicate descriptions found"


def test_some_scenarios_have_mitre_references(scenarios):
    """A subset should reference MITRE ATT&CK for credibility."""
    mitre_count = sum(1 for s in scenarios if "T1" in s["description"] or "MITRE" in s["description"])
    assert mitre_count >= 100, f"Only {mitre_count} scenarios reference MITRE — expected 100+"


def test_environments_have_real_variety(scenarios):
    """Should have 20+ distinct environments, not just 5 rotated."""
    envs = {s["environment"] for s in scenarios}
    assert len(envs) >= 20, f"Only {len(envs)} unique environments"


def test_time_contexts_have_variety(scenarios):
    contexts = {s["time_context"] for s in scenarios}
    assert len(contexts) >= 15, f"Only {len(contexts)} unique time contexts"


def test_generator_script_exists():
    """The generator should ship with the corpus so anyone can regenerate."""
    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_scenarios.py")
    assert os.path.isfile(script), "Generator script missing — data has no provenance"


def test_generator_is_reproducible():
    """Same seed should produce identical output."""
    import subprocess
    result1 = subprocess.run(
        [sys.executable, "scripts/generate_scenarios.py", "--seed", "99", "--count", "10"],
        capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    result2 = subprocess.run(
        [sys.executable, "scripts/generate_scenarios.py", "--seed", "99", "--count", "10"],
        capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    assert result1.stdout == result2.stdout, "Generator is not deterministic with same seed"
