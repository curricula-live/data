"""Structural graph auditing never promotes recorded claims into accepted truths."""
import json
from pathlib import Path

import pytest

from scripts.semantic_risk_audit import (
    ROOT,
    build_audit,
    directed_cycles,
    shortest_subtype_path,
    to_markdown,
)


def test_entire_canonical_corpus_is_audited_without_mutation():
    files = sorted((ROOT / "knowledge").glob("*.jsonl"))
    before = {path.name: path.read_bytes() for path in files}
    report = build_audit(ROOT)
    assert report["authorizes_import"] is False
    assert report["authorizes_new_inference_rules"] is False
    assert report["authorizes_publication"] is False
    assert report["origin"] == "canonical_data_jsonl_read_only"
    assert report["counts"]["concepts"] > 500
    assert report["counts"]["statements"] > 600
    assert len(report["predicate_questions"]) == report["counts"]["predicates"]
    assert before == {path.name: path.read_bytes() for path in files}
    assert report == build_audit(ROOT)


def test_array_double_relationship_is_a_review_candidate_not_an_error():
    result = build_audit(ROOT, focus="array")
    detail = result["focus"]
    assert detail and detail["slug"] == "array"
    facts = detail["direct_assertions"]
    assert len(facts) == 4
    assert {edge["predicate"] for edge in facts} == {"uses", "part_of", "subtype_of"}
    matches = detail["inverse_uses_part_of_candidates"]
    assert len(matches) == 1
    pair = matches[0]
    assert pair["subject"] == "array" and pair["object"] == "index"
    assert pair["status"] == "review_role_distinction_not_conflict"
    assert pair["uses_id"] in {e["id"] for e in facts}
    assert pair["part_of_id"] in {e["id"] for e in facts}
    text = to_markdown(result)
    assert "Not an asserted contradiction" in text


def test_integer_redundant_direct_classification_keeps_both_paths():
    result = build_audit(ROOT, focus="integer")
    assertion_ids = {row["id"] for row in result["focus"]["direct_assertions"]}
    findings = result["focus"]["redundant_direct_subtype_candidates"]
    number = next(row for row in findings if row["target"] == "number")
    assert number["id"] in assertion_ids
    assert len(number["alternative_premise_ids"]) >= 2
    assert number["status"] == "review_redundancy_not_semantic_error"


def test_subtype_cycle_detector_finds_only_true_directed_cycles():
    edges = {
        "alpha": [{"id": "a", "target": "beta"}],
        "beta": [{"id": "b", "target": "gamma"}],
        "gamma": [{"id": "c", "target": "alpha"}],
        "delta": [{"id": "d", "target": "gamma"}],
    }
    assert directed_cycles(set(edges), edges) == [["alpha", "beta", "gamma"]]
    assert directed_cycles(
        {"a", "b", "c"},
        {"a": [{"id": "a-b", "target": "b"}], "b": [{"id": "b-c", "target": "c"}]},
    ) == []


def test_redundancy_requires_an_alternative_two_edge_path():
    outgoing = {
        "a": [{"id": "direct", "target": "c"}, {"id": "ab", "target": "b"}],
        "b": [{"id": "bc", "target": "c"}],
    }
    assert shortest_subtype_path("a", "c", outgoing, exclude_id="direct") == ["ab", "bc"]
    assert shortest_subtype_path("a", "c", outgoing, exclude_id="direct", max_depth=1) is None


def test_absent_concept_and_unknown_predicate_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="Not in canonical concept"):
        build_audit(ROOT, focus="not-a-real-concept-from-this-audit")
    fake = tmp_path / "knowledge"
    fake.mkdir()
    original = ROOT / "knowledge"
    for name in ["concepts.jsonl", "statements.jsonl", "predicates.jsonl"]:
        (fake / name).write_text((original / name).read_text())
    statements = [json.loads(line) for line in (fake / "statements.jsonl").read_text().splitlines()]
    statements[0]["predicate"] = "fictional_unreviewed_predicate"
    (fake / "statements.jsonl").write_text("\n".join(json.dumps(v) for v in statements) + "\n")
    with pytest.raises(ValueError, match="Unknown predicate"):
        build_audit(tmp_path)
