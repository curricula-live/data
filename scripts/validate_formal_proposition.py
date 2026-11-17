"""Validate *synthetic* propositional proof certificates before proof checking.

Only validates syntax, finite formula complexity, and forward references.
Logical rule soundness / assumption discharge is checked by the paired API.
Does not modify canonical knowledge or a database.

Usage:
    python scripts/validate_formal_proposition.py tests/fixtures/propositional-deduction.synthetic.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "knowledge" / "formal-propositional-proof.v0.schema.json"
MAX_FORMULA_DEPTH = 12
MAX_FORMULA_NODES = 128
MAX_STEPS = 96


class PropositionalSchemaError(ValueError):
    pass


def _formula_size(formula: dict, depth: int = 1) -> int:
    if depth > MAX_FORMULA_DEPTH:
        raise PropositionalSchemaError("formula exceeds maximum depth")
    op = formula["op"]
    if op in ("atom", "top", "bottom"):
        return 1
    if op == "not":
        return 1 + _formula_size(formula["arg"], depth + 1)
    return 1 + _formula_size(formula["left"], depth + 1) + _formula_size(formula["right"], depth + 1)


def validate_propositional_proof(proof: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(proof))
    if errors:
        first = min(errors, key=lambda err: (str(list(err.absolute_path)), err.message))
        raise PropositionalSchemaError(
            f"Invalid proof at {list(first.absolute_path)}: {first.message}"
        )

    sizes = [_formula_size(proof["goal"])]
    seen: set[str] = set()
    rule_counts: dict[str, int] = {}
    assumptions = 0
    for step in proof["steps"]:
        rule = step["rule"]
        identifier = step["id"]
        if identifier in seen:
            raise PropositionalSchemaError(f"Duplicate step ID: {identifier}")
        # Only previous steps may be referenced, so no cycles or future facts.
        for field in (
            "left", "right", "conjunction", "implication", "antecedent",
            "assumption", "conclusion", "premise", "equivalence",
            "disjunction", "left_case", "right_case", "positive", "negative", "contradiction",
        ):
            if field in step and step[field] not in seen:
                raise PropositionalSchemaError(
                    f"{identifier}: {field} must reference an earlier step"
                )
        seen.add(identifier)
        rule_counts[rule] = rule_counts.get(rule, 0) + 1
        if rule == "assume":
            assumptions += 1
        if "formula" in step:
            sizes.append(_formula_size(step["formula"]))
        if "other" in step:
            sizes.append(_formula_size(step["other"]))
        if max(sizes) > MAX_FORMULA_NODES:
            raise PropositionalSchemaError("formula exceeds maximum node count")

    if proof["conclusion_step_id"] not in seen:
        raise PropositionalSchemaError("Conclusion step does not exist")
    return {
        "schema_version": proof["schema_version"],
        "synthetic_fixture_only": True,
        "well_formed": True,
        "semantically_checked": False,
        "may_publish": False,
        "steps": len(seen),
        "assumptions": assumptions,
        "max_formula_nodes": max(sizes),
        "rule_counts": dict(sorted(rule_counts.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    proof = json.loads(args.file.read_text(encoding="utf-8"))
    print(json.dumps(validate_propositional_proof(proof), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
