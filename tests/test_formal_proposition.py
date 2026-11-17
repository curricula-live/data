"""Strict syntax and forward-reference checks for synthetic propositional proofs."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from scripts.validate_formal_proposition import (
    MAX_FORMULA_DEPTH, PropositionalSchemaError,
    ROOT, validate_propositional_proof,
)

FIXTURE = ROOT / "tests" / "fixtures" / "propositional-deduction.synthetic.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_nested_implication_proof_is_syntax_only_and_nonpublishable():
    report = validate_propositional_proof(sample())
    assert report["well_formed"]
    assert report["may_publish"] is False
    assert report["semantically_checked"] is False
    assert report["assumptions"] == 2
    assert report["steps"] == 5
    assert report["rule_counts"] == {"assume": 2, "imp_elim": 1, "imp_intro": 2}


@pytest.mark.parametrize("change", [
    lambda p: p.update({"schema_version": "unapproved"}),
    lambda p: p.update({"extra": "unmodeled"}),
    lambda p: p["provenance"].update({"status": "published"}),
    lambda p: p["steps"][0].update({"rule": "trust_me"}),
    lambda p: p["steps"][0]["formula"].update({"op": "variable"}),
    lambda p: p["steps"][0]["formula"].update({"name": "bad name"}),
    lambda p: p["steps"][2].update({"antecedent": "s3"}),
    lambda p: p["steps"][2].update({"antecedent": "unknown"}),
    lambda p: p["steps"][1].update({"id": "h1"}),
    lambda p: p.update({"conclusion_step_id": "missing"}),
    lambda p: p["steps"][2].update({"formula": {"op": "atom", "name": "Q"}}),
    lambda p: p["steps"][2].update({"rule": "and_intro"}),
])
def test_invalid_certificates_fail_closed(change):
    proof = sample()
    change(proof)
    with pytest.raises(PropositionalSchemaError):
        validate_propositional_proof(proof)


def test_formula_tree_is_bounded_before_proof_checker():
    proof = sample()
    expr = {"op": "atom", "name": "P"}
    for _ in range(MAX_FORMULA_DEPTH + 2):
        expr = {"op": "not", "arg": expr}
    proof["goal"] = expr
    with pytest.raises(PropositionalSchemaError, match="maximum depth"):
        validate_propositional_proof(proof)


def test_raw_proof_does_not_touch_canonical_definitions_or_statements():
    paths = [ROOT / "knowledge" / "definitions.jsonl", ROOT / "knowledge" / "statements.jsonl"]
    old = [p.read_bytes() for p in paths]
    validate_propositional_proof(sample())
    assert old == [p.read_bytes() for p in paths]


def test_proof_is_deterministically_validated_without_external_context():
    assert validate_propositional_proof(sample()) == validate_propositional_proof(deepcopy(sample()))
