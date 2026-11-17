"""Read-only comparison of canonical and archived ontology model with synthetic fixtures."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.compare_historical_ontology import (
    ComparisonError, build_comparison, render_markdown,
)


def jsonl(path: Path, items: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in items),
        encoding="utf-8",
    )


def fixture(tmp_path):
    data, old = tmp_path / "data", tmp_path / "native-v2"
    (data / "knowledge").mkdir(parents=True, exist_ok=True)
    (old / "knowledge").mkdir(parents=True, exist_ok=True)
    (old / "manifest.json").write_text(json.dumps({
        "version": "1.0.0", "published": False,
        "automaticPublicationAllowed": False,
    }), encoding="utf-8")
    d = data / "knowledge"
    n = old / "knowledge"
    jsonl(d / "concepts.jsonl", [
        {"id": "d-a", "label": "Algorithm", "slug": "algorithm"},
        {"id": "d-b", "label": "Procedure", "slug": "procedure"},
    ])
    jsonl(d / "predicates.jsonl", [
        {"slug": "subtype_of"}, {"slug": "uses"},
    ])
    jsonl(d / "statements.jsonl", [{
        "id": "d-s1",
        "subject": {"kind": "concept", "id": "d-a"},
        "predicate": "uses",
        "object": {"kind": "concept", "id": "d-b"},
    }])
    jsonl(d / "definitions.jsonl", [])

    jsonl(n / "concepts.jsonl", [
        {"id": "h-a", "label": "Algorithm", "slug": "algorithm"},
        {"id": "h-b", "label": "Procedure", "slug": "procedure"},
        {"id": "h-c", "label": "Code", "slug": "code"},
    ])
    jsonl(n / "predicates.jsonl", [
        {"slug": "broader_topic"}, {"slug": "formal_scope"},
        {"slug": "has_semantic_specification"}, {"slug": "formal_op"},
    ])
    jsonl(n / "statements.jsonl", [
        {"id": "h-s1", "subject": {"kind": "concept", "id": "h-b"},
         "predicate": "broader_topic", "object": {"kind": "concept", "id": "h-a"}},
        {"id": "h-s2", "subject": {"kind": "concept", "id": "h-a"},
         "predicate": "has_semantic_specification",
         "object": {"kind": "literal", "datatype": "string", "value": "class_definition"}},
        {"id": "h-s3", "subject": {"kind": "statement", "id": "h-s2"},
         "predicate": "formal_scope",
         "object": {"kind": "literal", "datatype": "string", "value": "scoped_necessary"}},
    ])
    jsonl(n / "definitions.jsonl", [
        {"concept_id": "h-a", "statement_ids": ["h-s2", "h-s3"]},
    ])
    return data, old


def test_counts_distinguish_formal_grammar_from_concept_graph(tmp_path):
    data, old = fixture(tmp_path)
    result = build_comparison(data, old, ["algorithm"])
    assert result["status"] == "read_only_nonpublishing"
    assert result["identity_crosswalk_status"] == "not_verified_slug_comparison_only"
    assert result["canonical_counts"] == {
        "concepts": 2,
        "predicate_types": 2,
        "statements": 1,
        "definitions": 0,
        "concept_to_concept": 1,
        "concept_relation_predicates": {"uses": 1},
    }
    assert result["historical_counts"]["concepts"] == 3
    assert result["historical_counts"]["statements"] == 3
    assert result["historical_counts"]["predicate_types"] == 4
    assert result["historical_counts"]["formal_prefix_predicates"] == 2
    assert result["historical_counts"]["other_predicates"] == 2
    assert result["historical_counts"]["concept_to_concept"] == 1
    assert result["historical_counts"]["endpoint_kind_counts"] == {
        "concept->concept": 1, "concept->literal": 1, "statement->literal": 1
    }
    assert result["historical_counts"]["concept_relation_predicates"] == {"broader_topic": 1}


def test_same_slug_is_never_auto_approved_as_same_canonical_identity(tmp_path):
    data, old = fixture(tmp_path)
    entry = build_comparison(data, old, ["algorithm"])["concepts"][0]
    assert entry["lexical_slug_match_only"] is True
    assert entry["identity_equivalence_verified"] is False
    assert entry["canonical"]["concept_id"] == "d-a"
    assert entry["historical_native"]["concept_id"] == "h-a"
    assert entry["historical_native"]["incident_concept_edges"] == 1
    assert entry["historical_native"]["structured_record_summary"] == {
        "selected_statement_count": 2,
        "root_record_kinds": {"class_definition": 1},
        "scopes": ["scoped_necessary"],
    }
    markdown = render_markdown(build_comparison(data, old, ["algorithm"]))
    assert "not an approved identity crosswalk" in markdown
    assert "historical" in markdown.lower()
    assert "broader_topic" in markdown
    assert "Procedure" in markdown


def test_missing_slug_is_reported_not_invented(tmp_path):
    data, old = fixture(tmp_path)
    result = build_comparison(data, old, ["algorithm", "nonexistent"])
    unknown = result["concepts"][1]
    assert unknown["canonical"] is None
    assert unknown["historical_native"] is None
    assert unknown["identity_equivalence_verified"] is False
    assert "manual identity reconciliation" in render_markdown(result)


@pytest.mark.parametrize("change", [
    lambda r: r.update({"published": True}),
    lambda r: r.update({"automaticPublicationAllowed": True}),
])
def test_published_or_automatic_import_snapshots_are_refused(tmp_path, change):
    data, old = fixture(tmp_path)
    manifest_file = old / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    change(manifest)
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ComparisonError, match="unpublished historical"):
        build_comparison(data, old, ["algorithm"])


def test_missing_native_registry_and_duplicate_canonical_slug_fail_closed(tmp_path):
    data, old = fixture(tmp_path)
    (old / "knowledge/concepts.jsonl").unlink()
    with pytest.raises(ComparisonError, match="Missing"):
        build_comparison(data, old, ["algorithm"])
    data, old = fixture(tmp_path)
    concepts_file = data / "knowledge/concepts.jsonl"
    concepts_file.write_text(concepts_file.read_text() * 2)
    with pytest.raises(ComparisonError, match="Duplicate"):
        build_comparison(data, old, ["algorithm"])


def test_report_has_bounded_examples_and_writes_no_canonical_records(tmp_path):
    data, old = fixture(tmp_path)
    paths = list((data / "knowledge").glob("*.jsonl"))
    prior = [p.read_bytes() for p in paths]
    for limit in (1, 2):
        report = build_comparison(data, old, ["algorithm"], example_limit=limit)
        assert report["historical_counts"]["concept_to_concept"] == 1
    assert prior == [p.read_bytes() for p in paths]
    with pytest.raises(ComparisonError, match="Example limit"):
        build_comparison(data, old, ["algorithm"], example_limit=100)
    with pytest.raises(ComparisonError, match="distinct"):
        build_comparison(data, old, ["algorithm", "algorithm"])


def test_unknown_historical_concept_reference_fails_closed(tmp_path):
    data, old = fixture(tmp_path)
    statements = old / "knowledge/statements.jsonl"
    rows = [json.loads(line) for line in statements.read_text().splitlines()]
    rows[0]["object"]["id"] = "h-unknown"
    jsonl(statements, rows)
    with pytest.raises(ComparisonError, match="missing identity"):
        build_comparison(data, old, ["algorithm"])
