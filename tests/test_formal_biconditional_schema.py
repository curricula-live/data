"""Schema-level checks for the experimental biconditional introduction step."""
from __future__ import annotations

import json

import pytest

from scripts.validate_formal_proposition import (
    ROOT, PropositionalSchemaError, validate_propositional_proof
)

FIXTURE = ROOT / "tests/fixtures/propositional-biconditional.synthetic.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_iff_intro_is_structurally_admitted_but_not_semantically_certified():
    result = validate_propositional_proof(sample())
    assert result["rule_counts"] == {"assume": 2, "iff_intro": 1}
    assert result["semantically_checked"] is False
    assert result["synthetic_fixture_only"] is True
    assert result["may_publish"] is False


@pytest.mark.parametrize("tamper", [
    lambda m: m["steps"][2].update({"right": "unknown"}),
    lambda m: m["steps"][2].update({"left": "s1"}),
    lambda m: m["steps"][2].update({"extra": "accepted"}),
    lambda m: m["steps"][2].update({"rule": "unapproved_equivalence"}),
    lambda m: m["steps"][2].pop("right"),
    lambda m: m["steps"][2].update({"id": "h1"}),
    lambda m: m["provenance"].update({"status": "source_reviewed"}),
])
def test_forged_or_future_rule_steps_fail_syntax_validation(tamper):
    cert = sample()
    tamper(cert)
    with pytest.raises(PropositionalSchemaError):
        validate_propositional_proof(cert)
