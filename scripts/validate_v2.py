from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
SCHEMA = ROOT / "schema" / "knowledge"

FILES = {
    "concepts": KNOWLEDGE / "concepts.jsonl",
    "predicates": KNOWLEDGE / "predicates.jsonl",
    "statements": KNOWLEDGE / "statements.jsonl",
    "definitions": KNOWLEDGE / "definitions.jsonl",
}

SCHEMAS = {
    "concepts": SCHEMA / "concept.schema.json",
    "predicates": SCHEMA / "predicate.schema.json",
    "statements": SCHEMA / "statement.schema.json",
    "definitions": SCHEMA / "definition.schema.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        raise SystemExit(f"missing canonical file: {path.relative_to(ROOT)}")

    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path.relative_to(ROOT)}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{path.relative_to(ROOT)}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def validate_schema(name: str, rows: list[dict[str, Any]]) -> None:
    schema = load_json(SCHEMAS[name])
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for index, row in enumerate(rows, start=1):
        errors = sorted(validator.iter_errors(row), key=lambda error: list(error.path))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise SystemExit(f"{FILES[name].relative_to(ROOT)}:{index}: {details}")


def require_unique(values: list[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise SystemExit(f"duplicate {label}: {value}")
        seen.add(value)


def require_sorted(rows: list[dict[str, Any]], key: str, label: str) -> None:
    values = [str(row[key]) for row in rows]
    if values != sorted(values):
        raise SystemExit(f"{label} must be sorted by {key}")


def validate_references(
    concepts: list[dict[str, Any]],
    predicates: list[dict[str, Any]],
    statements: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
) -> None:
    concept_ids = {row["id"] for row in concepts}
    predicate_slugs = {row["slug"] for row in predicates}
    statement_ids = {row["id"] for row in statements}

    for row in statements:
        if row["predicate"] not in predicate_slugs:
            raise SystemExit(f"statement {row['id']} references unknown predicate {row['predicate']}")

        for side in ("subject", "object"):
            ref = row[side]
            kind = ref["kind"]
            if kind == "concept" and ref["id"] not in concept_ids:
                raise SystemExit(f"statement {row['id']} references unknown concept {ref['id']}")
            if kind == "statement" and ref["id"] not in statement_ids:
                raise SystemExit(f"statement {row['id']} references unknown statement {ref['id']}")

    defined_concepts: set[str] = set()
    for row in definitions:
        concept_id = row["concept_id"]
        if concept_id in defined_concepts:
            raise SystemExit(f"multiple canonical definitions for concept {concept_id}")
        defined_concepts.add(concept_id)

        if concept_id not in concept_ids:
            raise SystemExit(f"definition references unknown concept {concept_id}")
        for statement_id in row["statement_ids"]:
            if statement_id not in statement_ids:
                raise SystemExit(f"definition for {concept_id} references unknown statement {statement_id}")


def main() -> None:
    rows = {name: load_jsonl(path) for name, path in FILES.items()}

    for name, records in rows.items():
        validate_schema(name, records)

    require_unique([row["id"] for row in rows["concepts"]], "concept UUID")
    require_unique([row["slug"] for row in rows["concepts"]], "concept slug")
    require_unique([row["slug"] for row in rows["predicates"]], "predicate slug")
    require_unique([row["id"] for row in rows["statements"]], "statement UUID")

    require_sorted(rows["concepts"], "slug", "knowledge/concepts.jsonl")
    require_sorted(rows["predicates"], "slug", "knowledge/predicates.jsonl")
    require_sorted(rows["statements"], "id", "knowledge/statements.jsonl")
    require_sorted(rows["definitions"], "concept_id", "knowledge/definitions.jsonl")

    validate_references(
        rows["concepts"],
        rows["predicates"],
        rows["statements"],
        rows["definitions"],
    )

    print(
        "validated v2 knowledge: "
        f"{len(rows['concepts'])} concepts, "
        f"{len(rows['predicates'])} predicates, "
        f"{len(rows['statements'])} statements, "
        f"{len(rows['definitions'])} definitions"
    )


if __name__ == "__main__":
    main()
