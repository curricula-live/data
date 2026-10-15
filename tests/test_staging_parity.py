"""Unit tests for legacy PostgreSQL -> Git v2 migration parity.

No database access: live/staging parity must be run explicitly against a
staging database with an account restricted to SELECT.
"""
from copy import deepcopy
from uuid import UUID, uuid4

import pytest

from scripts.verify_staging_parity import (
    LegacySnapshot,
    compare_legacy_to_canonical,
    fetch_legacy_snapshot,
)

NAMESPACE = UUID("645d16b7-688a-5ffc-aa3d-8b6626ba1383")
C1 = "c74fe051-ac5e-521b-8770-3180fb0decb6"
C2 = "e9272fce-a569-5108-8def-0c35542cb640"
S1 = "26668f26-3e71-4dc6-8d3c-599e33425985"


def fixture() -> tuple[LegacySnapshot, dict]:
    source = LegacySnapshot(
        concept_slugs=("operating-system", "process"),
        predicate_slugs=("part_of",),
        relations=((S1, "operating-system", "part_of", "process"),),
    )
    state = {
        "manifest": {"counts": {"concepts": 2, "predicates": 1, "statements": 1}},
        "identity_ledger": [
            {"legacy_slug": "operating-system", "id": C1},
            {"legacy_slug": "process", "id": C2},
        ],
        "concepts": [
            {"id": C1, "slug": "os-renamed", "label": "Operating System"},
            {"id": C2, "slug": "process", "label": "Process"},
        ],
        "predicates": [{"slug": "part_of", "label": "part of"}],
        "statements": [
            {
                "id": S1,
                "subject": {"kind": "concept", "id": C1},
                "predicate": "part_of",
                "object": {"kind": "concept", "id": C2},
            }
        ],
        "statement_ledger": [S1],
    }
    return source, state


def test_identical_triples_with_renamed_slug_succeed() -> None:
    source, state = fixture()
    result = compare_legacy_to_canonical(source, **state)
    assert result["legacy_statements"] == 1
    assert result["canonical_concepts"] == 2


def test_semantic_mutation_of_statement_detected() -> None:
    source, state = fixture()
    state["statements"][0]["object"]["id"] = C1
    with pytest.raises(ValueError, match="content changed"):
        compare_legacy_to_canonical(source, **state)


def test_missing_statement_uuid_detected() -> None:
    source, state = fixture()
    state["statements"][0]["id"] = str(uuid4())
    with pytest.raises(ValueError, match="missing migrated statement"):
        compare_legacy_to_canonical(source, **state)


def test_post_migration_statement_additions_are_allowed() -> None:
    source, state = fixture()
    record = deepcopy(state["statements"][0])
    record["id"] = str(uuid4())
    state["statements"].append(record)
    result = compare_legacy_to_canonical(source, **state)
    assert result["canonical_statements"] == 2


def test_v1_legacy_relation_id_drift_detected() -> None:
    source, state = fixture()
    source = LegacySnapshot(
        source.concept_slugs,
        source.predicate_slugs,
        ((str(uuid4()), "operating-system", "part_of", "process"),),
    )
    with pytest.raises(ValueError, match="UUIDs differ"):
        compare_legacy_to_canonical(source, **state)


def test_missing_legacy_concept_detected() -> None:
    source, state = fixture()
    source = LegacySnapshot(("operating-system", "unexpected"), source.predicate_slugs, source.relations)
    with pytest.raises(ValueError, match="concept slugs do not match"):
        compare_legacy_to_canonical(source, **state)


def test_missing_runtime_predicate_detected() -> None:
    source, state = fixture()
    source = LegacySnapshot(source.concept_slugs, ("unknown",), source.relations)
    with pytest.raises(ValueError, match="predicates missing"):
        compare_legacy_to_canonical(source, **state)


def test_duplicate_ids_rejected() -> None:
    source, state = fixture()
    state["statements"].append(deepcopy(state["statements"][0]))
    with pytest.raises(ValueError, match="duplicate canonical statement"):
        compare_legacy_to_canonical(source, **state)


def test_legacy_snapshot_query_is_select_only() -> None:
    class StubCursor:
        def __init__(self):
            self.calls = []
            self.rows = iter([
                [("operating-system",), ("process",)],
                [("part_of",)],
                [(S1, "operating-system", "part_of", "process")],
            ])

        def execute(self, sql):
            assert sql.strip().lower().startswith("select ")
            self.calls.append(sql)

        def fetchall(self):
            return next(self.rows)

    cursor = StubCursor()
    snapshot = fetch_legacy_snapshot(cursor)
    assert len(cursor.calls) == 3
    assert snapshot.relations == ((S1, "operating-system", "part_of", "process"),)
