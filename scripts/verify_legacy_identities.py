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
    print(f"verified {count} migrated concept UUID identities (current slugs may differ)")


if __name__ == "__main__":
    main()
