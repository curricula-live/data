"""Regression contract for legacy-to-v2 UUID identities."""
import json
from pathlib import Path
from uuid import UUID, uuid5

import pytest

from scripts.verify_legacy_identities import verify_identity_ledger

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "645d16b7-688a-5ffc-aa3d-8b6626ba1383"


def record(slug: str) -> dict:
    return {"legacy_slug": slug, "id": str(uuid5(UUID(NAMESPACE), slug))}


def test_committed_identity_ledger_reconciles() -> None:
    manifest = json.loads((ROOT / "migration/legacy-v1/manifest.json").read_text())
    def rows(path: str) -> list[dict]:
        return [json.loads(line) for line in (ROOT / path).read_text().splitlines() if line.strip()]
    count = verify_identity_ledger(
        rows("knowledge/concepts.jsonl"),
        rows("migration/legacy-v1/concept-identities.jsonl"),
        namespace=manifest["concept_namespace_uuid"],
        expected_count=manifest["counts"]["concepts"],
    )
    assert count == 554


def test_slug_rename_preserves_canonical_identity() -> None:
    old = record("operating-system")
    new_concept = {"id": old["id"], "slug": "os-renamed", "label": "Operating system"}
    assert verify_identity_ledger(
        [new_concept], [old], namespace=NAMESPACE, expected_count=1
    ) == 1


def test_missing_historic_concept_fails() -> None:
    with pytest.raises(ValueError, match="missing"):
        verify_identity_ledger([], [record("thread")], namespace=NAMESPACE, expected_count=1)


def test_tampered_legacy_mapping_fails() -> None:
    entry = record("thread")
    entry["id"] = str(uuid5(UUID(NAMESPACE), "process"))
    with pytest.raises(ValueError, match="mapping changed"):
        verify_identity_ledger([{"id": entry["id"]}], [entry], namespace=NAMESPACE, expected_count=1)


def test_duplicate_legacy_slug_fails() -> None:
    entry = record("thread")
    with pytest.raises(ValueError, match="duplicate"):
        verify_identity_ledger(
            [{"id": entry["id"]}], [entry, entry], namespace=NAMESPACE, expected_count=2
        )
