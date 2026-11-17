"""Experimental formal-class-model grammar and identity validation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_formal_class_model import (
    ROOT, MAX_DEPTH, MAX_NODES, ModelValidationError, validate_model,
)

FIXTURE = ROOT / "tests" / "fixtures" / "formal-array.synthetic.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def concept(identifier: str):
    return {"op": "concept", "concept_id": identifier}


def test_synthetic_array_model_validates_but_never_becomes_true_or_publishable():
    result = validate_model(sample())
    assert result["valid"] is True
    assert result["node_count"] == 4
    assert result["operator_counts"] == {"and": 1, "concept": 2, "some": 1}
    assert result["relation"] == "necessary"
    assert result["may_publish"] is False
    assert result["scientific_claim_verified"] is False
    assert result["synthetic_fixture_only"] is True


@pytest.mark.parametrize("edit", [
    lambda d: d.update({"relation": "iff"}),
    lambda d: d.update({"schema_version": "canonical-knowledge.v1"}),
    lambda d: d.update({"unreviewed_new_field": "free form"}),
    lambda d: d["provenance"].update({"status": "accepted"}),
    lambda d: d.update({"subject_concept_id": "00000000-0000-4000-8000-000000000000"}),
    lambda d: d["expression"].update({"op": "arbitrary"}),
    lambda d: d["expression"].update({"args": [d["expression"]["args"][0]]}),
    lambda d: d["expression"]["args"][1].update({"property": "indexed_by"}),
])
def test_invalid_semantics_or_unknown_operators_fail_closed(edit):
    model = sample()
    edit(model)
    with pytest.raises(ModelValidationError):
        validate_model(model)


def test_boolean_operators_and_universal_restriction_are_typed():
    model = sample()
    array_ref = model["expression"]["args"][0]
    model["expression"] = {
        "op": "or",
        "args": [
            {"op": "not", "arg": array_ref},
            {"op": "only", "property": "uses", "filler": array_ref},
        ],
    }
    result = validate_model(model)
    assert result["operator_counts"] == {"concept": 2, "not": 1, "only": 1, "or": 1}


def test_reference_injection_does_not_accept_nonexistent_concepts_or_predicates():
    model = sample()
    ids = {model["subject_concept_id"]}
    with pytest.raises(ModelValidationError, match="unknown canonical concept"):
        validate_model(model, concept_ids=ids, predicate_slugs={"uses"}, statement_ids=set())
    ids.add("50484348-83a3-57b8-bbe4-114b66419300")
    ids.add("b4bf30bd-361a-5121-99f9-2c18afeaa60e")
    with pytest.raises(ModelValidationError, match="Unknown predicate"):
        validate_model(model, concept_ids=ids, predicate_slugs=set(), statement_ids=set())


def test_nested_expressions_are_bounded_before_rendering():
    model = sample()
    node = model["expression"]["args"][0]
    for _ in range(MAX_DEPTH + 2):
        node = {"op": "not", "arg": node}
    model["expression"] = node
    with pytest.raises(ModelValidationError, match="maximum depth"):
        validate_model(model)


def test_model_is_not_saved_as_a_canonical_definition():
    before = (ROOT / "knowledge" / "definitions.jsonl").read_bytes()
    validate_model(sample())
    after = (ROOT / "knowledge" / "definitions.jsonl").read_bytes()
    assert after == before
    assert sample()["provenance"]["supporting_statement_ids"] == []
