"""Source crosswalk candidates are unverified and never import semantic claims."""
import json
from pathlib import Path

import pytest

from scripts.source_identity_candidates import ROOT, build_candidates, to_markdown


def _manifest(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "v2-source-discovery.jsonl"
    path.write_text(
        "\n".join(json.dumps(row) for row in records) + "\n",
        encoding="utf-8",
    )
    return path


def _record(label: str, fragment: str) -> dict:
    return {
        "source_id": "example-unverified-source",
        "source_version": "synthetic-fixture-v0",
        "source_uri": "https://example.invalid/nodes/" + fragment,
        "label": label,
        "rights_status": "unverified",
    }


def test_label_matches_only_suggest_unverified_identity(tmp_path):
    report = build_candidates(_manifest(tmp_path, [
        _record("Array", "array"),
        _record("TCP", "tcp"),
        _record("Array", "array-variant"),
    ]))
    assert report["record_count"] == 3
    assert report["authorizes_ontology_admission"] is False
    assert report["authorizes_canonical_mutation"] is False
    assert report["authorizes_publication"] is False
    items = report["records"]
    assert len({r["source_uri"] for r in items}) == 3
    named_array = [r for r in items if r["label"] == "Array"]
    assert len(named_array) == 2
    assert all(row["candidates"][0]["canonical_slug"] == "array" for row in named_array)
    assert all(row["candidates"][0]["identity_verified"] is False for row in named_array)
    assert all(row["candidates"][0]["alignment_decision"] == "not_established" for row in named_array)
    tcp = next(r for r in items if r["label"] == "TCP")
    assert not tcp["candidates"]
    assert tcp["may_import_assertions"] is False
    assert report == build_candidates(_manifest(tmp_path, [
        _record("Array", "array-variant"),
        _record("TCP", "tcp"),
        _record("Array", "array"),
    ]))
    assert "unreviewed" in to_markdown(report).lower()


def test_explicit_candidate_is_still_not_a_verified_mapping(tmp_path):
    record = _record("A potential binding", "source-42")
    record["candidate_slug"] = "variable"
    report = build_candidates(_manifest(tmp_path, [record]))
    guess = report["records"][0]["candidates"][0]
    assert guess["canonical_slug"] == "variable"
    assert guess["suggestion_basis"] == "reviewer_proposed_slug"
    assert guess["identity_verified"] is False
    assert report["records"][0]["review_tier"] == "core"


@pytest.mark.parametrize("unsupported", [
    {"predicate": "subtype_of", "subject": "array", "object": "collection"},
    {"triples": [{"s": "a", "p": "x", "o": "b"}]},
    {"rights_status": "approved"},
    {"source_checksum_sha256": "invalid"},
    {"source_uri": "file:///tmp/local-source"},
    {"source_uri": "https://user:password@example.invalid/array"},
    {"candidate_slug": "../invalid"},
])
def test_untrusted_or_semantic_inputs_fail_closed(tmp_path, unsupported):
    record = _record("Array", "array")
    record.update(unsupported)
    with pytest.raises(ValueError):
        build_candidates(_manifest(tmp_path, [record]))


def test_duplicate_source_uri_per_version_is_rejected(tmp_path):
    record = _record("Array", "array")
    with pytest.raises(ValueError, match="Repeated native source URI"):
        build_candidates(_manifest(tmp_path, [record, record]))


def test_canonical_data_is_not_mutated_even_with_candidates(tmp_path):
    paths = sorted((ROOT / "knowledge").glob("*.jsonl"))
    original = {p.name: p.read_bytes() for p in paths}
    report = build_candidates(_manifest(tmp_path, [_record("Array", "array")]))
    assert report["origin"] == "source_discovery_manifest_unverified"
    assert original == {p.name: p.read_bytes() for p in paths}
