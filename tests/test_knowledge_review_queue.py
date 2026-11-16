"""Noncanonical review queue: deterministic, identity-safe, never approving facts."""
import json
from pathlib import Path

import pytest

from scripts.knowledge_review_queue import build_report, to_markdown

ROOT = Path(__file__).resolve().parents[1]


def test_ranked_queue_is_read_only_and_has_no_authorized_inference():
    report = build_report(ROOT)
    assert report["authorizes_import"] is False
    assert report["authorizes_publication"] is False
    assert len(report["predicate_audit"]) == report["current_corpus"]["predicates"]
    assert all(row["logical_rules_authorized"] == [] for row in report["predicate_audit"])
    assert all(row["status"] == "review_candidate_only" for row in report["priority_queue"])
    assert report["current_corpus"]["concepts"] > 0


def test_core_and_missing_candidates_retain_distinct_statuses():
    rows = {row["slug"]: row for row in build_report(ROOT)["priority_queue"]}
    assert rows["array"]["canonical_concept_id"]
    assert rows["array"]["direct_statement_count"] > 0
    assert rows["tcp"]["canonical_concept_id"] is None
    assert rows["tcp"]["identity_mapping_review"] == "pending"
    assert rows["integer"]["tier"] == "core"
    assert rows["index"]["tier"] == "supporting"
    assert rows["color"]["tier"] == "defer_unless_needed"


def test_report_is_deterministic_and_does_not_mutate_canonical_files():
    files = list((ROOT / "knowledge").glob("*.jsonl"))
    before = {p.name: p.read_bytes() for p in files}
    first = build_report(ROOT)
    assert first == build_report(ROOT)
    assert "Non-canonical concept review queue" in to_markdown(first)
    assert before == {p.name: p.read_bytes() for p in files}


def test_dossier_contains_original_directed_assertions_and_uuid_links():
    report = build_report(ROOT)
    array = next(row for row in report["priority_queue"] if row["slug"] == "array")
    assertions = array["recorded_statements"]
    assert len(assertions) == array["direct_statement_count"]
    assert all(
        row["source_verification"] == "not_established_by_core_statement_record"
        and row["review_status"] == "pending"
        for row in assertions
    )
    assert any(row["subject"] == "array" and row["predicate"] == "uses"
               and row["object"] == "index" for row in assertions)
    assert any(row["subject"] == "index" and row["predicate"] == "part_of"
               and row["object"] == "array" for row in assertions)
    text = to_markdown(report, detail_slug="array")
    assert "Recorded statements to review: array" in text
    assert all(row["id"] in text for row in assertions)


def test_duplicate_priority_entries_are_rejected(tmp_path):
    data = json.loads((ROOT / "pipeline/concept-review-priorities.json").read_text())
    data["priorities"].append(data["priorities"][0])
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Duplicate concept"):
        build_report(ROOT, path)


def test_marked_approved_queue_is_rejected(tmp_path):
    data = json.loads((ROOT / "pipeline/concept-review-priorities.json").read_text())
    data["status"] = "approved"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="non-publishable"):
        build_report(ROOT, path)
