"""Validate experimental typed class models without changing canonical knowledge.

The accepted canonical definition shape (concept_id + statement_ids) is
intentionally unchanged. Synthetic models from this module are NOT publishable.

Usage:
    python scripts/validate_formal_class_model.py tests/fixtures/formal-array.synthetic.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "knowledge" / "formal-class-model.v0.schema.json"
MAX_DEPTH = 10
MAX_NODES = 96


class ModelValidationError(ValueError):
    """Structural or referential failure in a synthetic formal model."""


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_model(
    model: dict[str, Any],
    *,
    concept_ids: set[str] | None = None,
    predicate_slugs: set[str] | None = None,
    statement_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Validate schema, referenced identities, and bounded syntax complexity.

    Callers may supply explicit fixture registries. Omitting them means the
    checked-in canonical *identity registries* are used, not source evidence.
    Passing validation proves well-formedness only.
    """
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(model), key=lambda error: str(list(error.path)))
    if errors:
        first = errors[0]
        raise ModelValidationError(
            f"Invalid formal class model at {list(first.path)}: {first.message}"
        )

    if concept_ids is None:
        concept_ids = {row["id"] for row in read_jsonl(ROOT / "knowledge" / "concepts.jsonl")}
    if predicate_slugs is None:
        predicate_slugs = {row["slug"] for row in read_jsonl(ROOT / "knowledge" / "predicates.jsonl")}
    if statement_ids is None:
        statement_ids = {row["id"] for row in read_jsonl(ROOT / "knowledge" / "statements.jsonl")}

    if model["subject_concept_id"] not in concept_ids:
        raise ModelValidationError("Subject references an unknown canonical concept UUID")
    for identifier in model["provenance"]["supporting_statement_ids"]:
        if identifier not in statement_ids:
            raise ModelValidationError(f"Unknown supporting statement UUID: {identifier}")

    node_count = 0
    operators: dict[str, int] = {}

    def walk(expr: dict[str, Any], depth: int) -> None:
        nonlocal node_count
        if depth > MAX_DEPTH:
            raise ModelValidationError(f"Expression exceeds maximum depth {MAX_DEPTH}")
        node_count += 1
        if node_count > MAX_NODES:
            raise ModelValidationError(f"Expression exceeds maximum nodes {MAX_NODES}")
        op = expr["op"]
        operators[op] = operators.get(op, 0) + 1
        if op == "concept":
            if expr["concept_id"] not in concept_ids:
                raise ModelValidationError("Expression references an unknown canonical concept UUID")
        elif op in ("some", "only"):
            if expr["property"] not in predicate_slugs:
                raise ModelValidationError(f"Unknown predicate: {expr['property']}")
            walk(expr["filler"], depth + 1)
        elif op in ("and", "or"):
            for term in expr["args"]:
                walk(term, depth + 1)
        elif op == "not":
            walk(expr["arg"], depth + 1)
        else:
            raise ModelValidationError(f"Unrecognized operator {op}")

    walk(model["expression"], 1)
    return {
        "schema_version": model["schema_version"],
        "valid": True,
        "synthetic_fixture_only": True,
        "may_publish": False,
        "scientific_claim_verified": False,
        "relation": model["relation"],
        "node_count": node_count,
        "max_depth": MAX_DEPTH,
        "operator_counts": dict(sorted(operators.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    args = parser.parse_args()
    path = args.model.resolve()
    # Allow arbitrary reads of user-supplied fixture files, but never write.
    model = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(validate_model(model), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
