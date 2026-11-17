"""Validate hypothetical scoped subtype proof certificates against immutable JSONL snapshots.

The current canonical statements have no reviewed semantic scope field. Each
recorded premise's assumed_scope is therefore a hypothesis supplied by the
experiment, never a classification inferred or authenticated from the source.

Only syntax and exact UUID/snapshot provenance are checked here. The paired
pure API checker independently verifies subtype transitivity and the goal.

Usage:
  python scripts/validate_scoped_subtype_proof.py tests/fixtures/scoped-array-subtype.synthetic.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema/knowledge/formal-scoped-subtype-proof.v0.schema.json"


class ScopedSubtypeValidationError(ValueError):
    pass


def validate_scoped_subtype_proof(
    certificate: dict,
    *,
    concepts_bytes: bytes | None = None,
    statements_bytes: bytes | None = None,
) -> dict:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(certificate))
    if errors:
        error = min(errors, key=lambda e: (str(list(e.absolute_path)), e.message))
        raise ScopedSubtypeValidationError(
            f"Invalid subtype certificate at {list(error.absolute_path)}: {error.message}"
        )

    if concepts_bytes is None:
        concepts_bytes = (ROOT / "knowledge/concepts.jsonl").read_bytes()
    if statements_bytes is None:
        statements_bytes = (ROOT / "knowledge/statements.jsonl").read_bytes()

    for name, data in (("concepts", concepts_bytes), ("statements", statements_bytes)):
        checksum = "sha256:" + sha256(data).hexdigest()
        if certificate["snapshot"][f"{name}_sha256"] != checksum:
            raise ScopedSubtypeValidationError(f"Stale or mismatched {name} snapshot")

    try:
        concepts = [json.loads(line) for line in concepts_bytes.decode("utf-8").splitlines() if line.strip()]
        statements = [json.loads(line) for line in statements_bytes.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError) as error:
        raise ScopedSubtypeValidationError("Snapshot contains invalid JSONL") from error

    known_concepts = {c["id"] for c in concepts}
    known_statements = {s["id"]: s for s in statements}
    if len(known_concepts) != len(concepts) or len(known_statements) != len(statements):
        raise ScopedSubtypeValidationError("Duplicate concept or statement UUID")
    if certificate["goal"]["subject_concept_id"] not in known_concepts or certificate["goal"]["object_concept_id"] not in known_concepts:
        raise ScopedSubtypeValidationError("Goal contains unknown canonical concept UUID")

    known_steps: set[str] = set()
    source_ids: set[str] = set()
    rule_count = 0
    for step in certificate["steps"]:
        if step["id"] in known_steps:
            raise ScopedSubtypeValidationError("Duplicate proof step ID")
        if step["rule"] == "recorded_subtype":
            sid = step["statement_id"]
            if sid in source_ids:
                raise ScopedSubtypeValidationError("Duplicate recorded premise UUID")
            source_ids.add(sid)
            original = known_statements.get(sid)
            if original is None:
                raise ScopedSubtypeValidationError(f"Unknown canonical assertion UUID: {sid}")
            if (
                original.get("predicate") != "subtype_of"
                or original.get("subject", {}).get("kind") != "concept"
                or original.get("object", {}).get("kind") != "concept"
            ):
                raise ScopedSubtypeValidationError("Recorded premise must be a concept-to-concept subtype_of")
            if step["assumed_scope"] != certificate["scope"]:
                raise ScopedSubtypeValidationError("Premise's hypothetical scope must match proof scope")
        else:
            rule_count += 1
            if step["left"] not in known_steps or step["right"] not in known_steps:
                raise ScopedSubtypeValidationError("Transitivity steps must reference earlier steps")
        known_steps.add(step["id"])

    if certificate["conclusion_step_id"] not in known_steps:
        raise ScopedSubtypeValidationError("Conclusion refers to unknown step ID")
    if not rule_count:
        raise ScopedSubtypeValidationError("Proof needs at least one explicit transitivity step")

    return {
        "schema_version": certificate["schema_version"],
        "scope": certificate["scope"],
        "recorded_premise_ids": sorted(source_ids),
        "rule_count": rule_count,
        "step_count": len(known_steps),
        "canonical_snapshot_pinned": True,
        "semantic_context_from_source_verified": False,
        "proof_semantics_verified": False,
        "scientific_claims_verified": False,
        "may_publish": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path)
    args = parser.parse_args()
    report = validate_scoped_subtype_proof(json.loads(args.certificate.read_text(encoding="utf-8")))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
