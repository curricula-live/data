"""Read-only verification of the one-time v1 -> v2 concept UUID ledger.

The UUIDv5 derivation applies only to the legacy migration cohort. Published
UUIDs remain authoritative even when the current human-readable slug changes.
This command never writes Git content or the runtime database.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_identity_ledger(
    concepts: list[dict],
    ledger: list[dict],
    *,
    namespace: str,
    expected_count: int,
) -> int:
    """Validate the committed historic slug->UUID mapping without rekeying.

    The concept's *current* slug is deliberately not compared to legacy_slug:
    a legitimate rename must preserve its UUID.
    """
    if expected_count <= 0 or len(ledger) != expected_count:
        raise ValueError(f"legacy ledger size mismatch: expected {expected_count}, found {len(ledger)}")

    concept_ids = [record["id"] for record in concepts]
    if len(set(concept_ids)) != len(concept_ids):
        raise ValueError("duplicate canonical concept UUID")
    available_ids = set(concept_ids)
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    migration_namespace = UUID(namespace)

    for record in ledger:
        legacy_slug = record["legacy_slug"]
        concept_id = str(UUID(record["id"]))
        if legacy_slug in seen_slugs or concept_id in seen_ids:
            raise ValueError(f"duplicate legacy identity: {legacy_slug}")
        seen_slugs.add(legacy_slug)
        seen_ids.add(concept_id)
        if uuid5(migration_namespace, legacy_slug) != UUID(concept_id):
            raise ValueError(f"legacy UUIDv5 mapping changed: {legacy_slug}")
        if concept_id not in available_ids:
            raise ValueError(f"legacy concept missing from canonical corpus: {concept_id}")
    return len(seen_ids)


def main() -> None:
    root = ROOT
    manifest = json.loads((root / "migration/legacy-v1/manifest.json").read_text(encoding="utf-8"))
    count = verify_identity_ledger(
        read_jsonl(root / "knowledge/concepts.jsonl"),
        read_jsonl(root / "migration/legacy-v1/concept-identities.jsonl"),
        namespace=manifest["concept_namespace_uuid"],
        expected_count=manifest["counts"]["concepts"],
    )
    statement_count = verify_imported_statements(root)
    print(f"verified {count} migrated concept UUID identities and {statement_count} migrated statement UUIDs")



def verify_statement_ledger(
    statements: list[dict],
    legacy_ids: list[str],
    *,
    concept_ids: set[str],
    predicate_slugs: set[str],
    expected_count: int,
) -> int:
    """Check preservation of imported statement identities and graph references.

    The legacy UUID list is immutable evidence of the migration cohort.
    New post-migration statements are allowed; removing or rekeying an imported
    statement is not. Academic truth/review status is deliberately NOT inferred.
    """
    if len(legacy_ids) != expected_count or len(set(legacy_ids)) != expected_count:
        raise ValueError("legacy statement UUID ledger count or uniqueness mismatch")
    for identifier in legacy_ids:
        if str(UUID(identifier)) != identifier:
            raise ValueError(f"noncanonical legacy statement UUID: {identifier}")

    rows_by_id: dict[str, dict] = {}
    for row in statements:
        identifier = row["id"]
        if str(UUID(identifier)) != identifier:
            raise ValueError(f"noncanonical statement UUID: {identifier}")
        if identifier in rows_by_id:
            raise ValueError(f"duplicate statement UUID: {identifier}")
        rows_by_id[identifier] = row

    missing = set(legacy_ids) - rows_by_id.keys()
    if missing:
        raise ValueError(f"missing imported statement UUID: {sorted(missing)[0]}")

    for identifier, statement in rows_by_id.items():
        if statement["predicate"] not in predicate_slugs:
            raise ValueError(f"unknown predicate in statement {identifier}")
        for side in ("subject", "object"):
            ref = statement[side]
            if ref["kind"] == "concept" and ref["id"] not in concept_ids:
                raise ValueError(f"dangling concept {side} in statement {identifier}")
            if ref["kind"] == "statement" and ref["id"] not in rows_by_id:
                raise ValueError(f"dangling statement {side} in statement {identifier}")
            if ref["kind"] == "literal" and side == "subject":
                raise ValueError(f"literal cannot be a statement subject: {identifier}")

    return len(legacy_ids)


def verify_imported_statements(root: Path = ROOT) -> int:
    """Validate migration cohort against current source without DB I/O."""
    manifest = json.loads(
        (root / "migration/legacy-v1/manifest.json").read_text(encoding="utf-8")
    )
    concepts = read_jsonl(root / "knowledge/concepts.jsonl")
    predicates = read_jsonl(root / "knowledge/predicates.jsonl")
    statements = read_jsonl(root / "knowledge/statements.jsonl")
    legacy_ids = [
        line for line in (
            root / "migration/legacy-v1/statement-uuids.txt"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return verify_statement_ledger(
        statements, legacy_ids,
        concept_ids={row["id"] for row in concepts},
        predicate_slugs={row["slug"] for row in predicates},
        expected_count=manifest["counts"]["statements"],
    )


if __name__ == "__main__":
    main()
