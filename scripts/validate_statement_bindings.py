"""Read-only verification of synthetic atom → canonical statement UUID bindings.

A binding lets a propositional formula name an existing recorded assertion.
It does not make the assertion true and never grants an inference rule over
the predicate. Both canonical file hashes must match, so drift is visible.

Usage:
    python scripts/validate_statement_bindings.py tests/fixtures/recorded-array-bindings.synthetic.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "knowledge" / "formal-statement-bindings.v0.schema.json"


class StatementBindingError(ValueError):
    pass


def _records(payload: bytes, label: str) -> list[dict]:
    try:
        result = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise StatementBindingError(f"{label}: invalid JSONL input") from exc
    if not all(isinstance(row, dict) for row in result):
        raise StatementBindingError(f"{label}: expected JSON objects")
    return result


def validate_statement_bindings(
    binding: dict,
    *,
    concepts_bytes: bytes | None = None,
    statements_bytes: bytes | None = None,
) -> dict:
    validator = Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    errors = list(validator.iter_errors(binding))
    if errors:
        err = min(errors, key=lambda error: (str(list(error.absolute_path)), error.message))
        raise StatementBindingError(f"Invalid binding at {list(err.absolute_path)}: {err.message}")

    if concepts_bytes is None:
        concepts_bytes = (ROOT / "knowledge" / "concepts.jsonl").read_bytes()
    if statements_bytes is None:
        statements_bytes = (ROOT / "knowledge" / "statements.jsonl").read_bytes()

    for name, payload in (("concepts", concepts_bytes), ("statements", statements_bytes)):
        fingerprint = "sha256:" + sha256(payload).hexdigest()
        if binding["snapshot"][f"{name}_sha256"] != fingerprint:
            raise StatementBindingError(f"{name}: stale or mismatched canonical snapshot")

    concept_rows = _records(concepts_bytes, "concepts")
    statement_rows = _records(statements_bytes, "statements")
    concepts = {row["id"]: row for row in concept_rows}
    statements = {row["id"]: row for row in statement_rows}
    if len(concepts) != len(concept_rows) or len(statements) != len(statement_rows):
        raise StatementBindingError("Duplicate canonical UUID in supplied snapshot")

    seen_atoms: set[str] = set()
    seen_ids: set[str] = set()
    projection = []
    for entry in binding["bindings"]:
        atom, sid = entry["atom"], entry["statement_id"]
        if atom in seen_atoms or sid in seen_ids:
            raise StatementBindingError("Duplicate atom name or duplicate statement identity")
        seen_atoms.add(atom)
        seen_ids.add(sid)
        source = statements.get(sid)
        if source is None:
            raise StatementBindingError(f"Unknown recorded statement UUID: {sid}")
        if source["subject"].get("kind") != "concept" or source["object"].get("kind") != "concept":
            raise StatementBindingError("v0 supports concept-to-concept statements only")
        source_id = source["subject"]["id"]
        target_id = source["object"]["id"]
        if source_id not in concepts or target_id not in concepts:
            raise StatementBindingError("Statement endpoint references an unknown canonical concept")
        projection.append({
            "atom": atom,
            "statement_id": sid,
            "subject_concept_id": source_id,
            "subject_slug": concepts[source_id]["slug"],
            "predicate": source["predicate"],
            "object_concept_id": target_id,
            "object_slug": concepts[target_id]["slug"],
            "scientific_status": "recorded_not_reviewed",
        })

    return {
        "schema_version": binding["schema_version"],
        "snapshot": dict(binding["snapshot"]),
        "bindings": sorted(projection, key=lambda row: row["atom"]),
        "registered_statement_identities_verified": True,
        "scientific_claims_verified": False,
        "semantic_inference_rules_authorized": [],
        "may_publish": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binding", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.binding.read_text(encoding="utf-8"))
    print(json.dumps(validate_statement_bindings(payload), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
