"""Validate scoped semantic proof structure without publishing a graph fact."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from scripts.validate_scoped_subtype_proof import (
    ROOT, ScopedSubtypeValidationError, validate_scoped_subtype_proof
)

FIXTURE = ROOT / "tests/fixtures/scoped-array-subtype.synthetic.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_real_array_proof_references_original_canonical_premise_uuids():
    result = validate_scoped_subtype_proof(sample())
    assert result["scope"] == "hypothetical_shared_taxonomy"
    assert result["recorded_premise_ids"] == [
        "048adf33-0701-43de-998f-20c299388f51",
        "15ead31d-e970-4aad-a4f8-7c9fccf3097a",
    ]
    assert result["step_count"] == 3
    assert result["rule_count"] == 1
    assert result["canonical_snapshot_pinned"] is True
    assert result["semantic_context_from_source_verified"] is False
    assert result["scientific_claims_verified"] is False
    assert result["proof_semantics_verified"] is False
    assert result["may_publish"] is False
    assert result == validate_scoped_subtype_proof(deepcopy(sample()))


@pytest.mark.parametrize("mutate", [
    lambda p: p.update({"schema_version": "unapproved"}),
    lambda p: p.update({"extra": "metadata"}),
    lambda p: p.update({"scope": "verified_universal"}),
    lambda p: p["provenance"].update({"status": "reviewed"}),
    lambda p: p["provenance"].update({"scope_origin": "from_source"}),
    lambda p: p["snapshot"].update({"statements_sha256": "sha256:" + "0" * 64}),
    lambda p: p["snapshot"].update({"concepts_sha256": "sha256:" + "f" * 64}),
    lambda p: p["steps"][0].update({"assumed_scope": "hypothetical_other"}),
    lambda p: p["steps"][0].update({"statement_id": "00000000-0000-4000-8000-000000000000"}),
    lambda p: p["steps"][0].update({"unsupported": True}),
    lambda p: p["steps"][1].update({"id": "h1"}),
    lambda p: p["steps"][1].update({"statement_id": p["steps"][0]["statement_id"]}),
    lambda p: p["steps"][2].update({"left": "s2"}),
    lambda p: p["steps"][2].update({"rule": "subtype_of_inverse"}),
    lambda p: p["goal"].update({"predicate": "uses"}),
    lambda p: p.update({"conclusion_step_id": "no_such_step"}),
    lambda p: p["steps"].pop(),
])
def test_malformed_snapshot_scope_or_step_fails(mutate):
    proof = sample()
    mutate(proof)
    with pytest.raises(ScopedSubtypeValidationError):
        validate_scoped_subtype_proof(proof)


def test_one_recorded_uses_predicate_cannot_be_smuggled_into_transitivity():
    p = sample()
    data = (ROOT / "knowledge/statements.jsonl").read_bytes()
    entries = [json.loads(line) for line in data.splitlines()]
    matching = next(row for row in entries if row["id"] == p["steps"][1]["statement_id"])
    matching["predicate"] = "uses"
    updated = b"\n".join(json.dumps(row).encode() for row in entries) + b"\n"
    p["snapshot"]["statements_sha256"] = "sha256:" + sha256(updated).hexdigest()
    with pytest.raises(ScopedSubtypeValidationError, match="concept-to-concept subtype_of"):
        validate_scoped_subtype_proof(p, statements_bytes=updated)


def test_snapshot_file_drift_is_detected_even_if_identity_exists():
    p = sample()
    concepts = (ROOT / "knowledge/concepts.jsonl").read_bytes()
    with pytest.raises(ScopedSubtypeValidationError, match="Stale or mismatched concepts"):
        validate_scoped_subtype_proof(p, concepts_bytes=concepts + b"\n")


def test_canonical_files_are_never_edited_or_auto_published():
    paths = [
        ROOT / "knowledge/concepts.jsonl",
        ROOT / "knowledge/statements.jsonl",
        ROOT / "knowledge/definitions.jsonl",
    ]
    before = [path.read_bytes() for path in paths]
    validate_scoped_subtype_proof(sample())
    assert before == [path.read_bytes() for path in paths]
