"""Snapshot-bound, nonpublishing recorded-statement atom binding tests."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from scripts.validate_statement_bindings import (
    ROOT, StatementBindingError, validate_statement_bindings,
)

FIXTURE = ROOT / "tests" / "fixtures" / "recorded-array-bindings.synthetic.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_actual_canonical_statements_become_opaque_propositional_atoms():
    result = validate_statement_bindings(sample())
    assert result["registered_statement_identities_verified"] is True
    assert result["scientific_claims_verified"] is False
    assert result["semantic_inference_rules_authorized"] == []
    assert result["may_publish"] is False
    assert [(row["atom"], row["subject_slug"], row["predicate"], row["object_slug"])
            for row in result["bindings"]] == [
        ("P", "array", "subtype_of", "collection"),
        ("Q", "collection", "subtype_of", "data"),
    ]
    assert all(row["scientific_status"] == "recorded_not_reviewed" for row in result["bindings"])


@pytest.mark.parametrize("mutate", [
    lambda m: m.update({"scope": "published_verified"}),
    lambda m: m.update({"extra": True}),
    lambda m: m["provenance"].update({"status": "approved"}),
    lambda m: m["provenance"].update({"source_scientific_review": "complete"}),
    lambda m: m["snapshot"].update({"concepts_sha256": "sha256:" + "0" * 64}),
    lambda m: m["snapshot"].update({"statements_sha256": "sha256:" + "f" * 64}),
    lambda m: m["bindings"].append(deepcopy(m["bindings"][0])),
    lambda m: m["bindings"].append({"atom": "R", "statement_id": m["bindings"][0]["statement_id"]}),
    lambda m: m["bindings"][0].update({"statement_id": "00000000-0000-4000-8000-000000000000"}),
    lambda m: m["bindings"][0].update({"atom": "not an atom"}),
    lambda m: m["bindings"][0].update({"predicate": "subtype_of"}),
])
def test_unknown_stale_misleading_or_duplicate_bindings_are_rejected(mutate):
    data = sample()
    mutate(data)
    with pytest.raises(StatementBindingError):
        validate_statement_bindings(data)


def test_external_snapshot_mutation_is_detected_even_with_matching_uuid():
    data = sample()
    statements = (ROOT / "knowledge" / "statements.jsonl").read_bytes()
    modified = statements.replace(b'"predicate":"subtype_of"', b'"predicate":"part_of"', 1)
    assert modified != statements
    with pytest.raises(StatementBindingError, match="stale or mismatched"):
        validate_statement_bindings(data, statements_bytes=modified)


def test_checked_manifest_never_mutates_canonical_data_files():
    paths = [
        ROOT / "knowledge" / "concepts.jsonl",
        ROOT / "knowledge" / "statements.jsonl",
        ROOT / "knowledge" / "definitions.jsonl",
    ]
    before = [p.read_bytes() for p in paths]
    assert validate_statement_bindings(sample()) == validate_statement_bindings(sample())
    assert before == [p.read_bytes() for p in paths]


def test_referenced_literal_statement_fails_without_upcasting_it_to_concept():
    # Construct a self-consistent disposable snapshot with a literal object.
    data = sample()
    contents = (ROOT / "knowledge" / "statements.jsonl").read_bytes()
    rows = [json.loads(line) for line in contents.splitlines()]
    replacement = next(row for row in rows if row["id"] == data["bindings"][0]["statement_id"])
    replacement["object"] = {"kind": "literal", "datatype": "string", "value": "not a concept"}
    modified = b"\n".join(json.dumps(row).encode() for row in rows) + b"\n"
    data["snapshot"]["statements_sha256"] = "sha256:" + sha256(modified).hexdigest()
    with pytest.raises(StatementBindingError, match="concept-to-concept"):
        validate_statement_bindings(data, statements_bytes=modified)
