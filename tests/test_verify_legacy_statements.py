"""Read-only regression tests for the imported statement UUID cohort."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.verify_legacy_identities import verify_imported_statements, verify_statement_ledger

ROOT = Path(__file__).resolve().parents[1]
C1 = "c74fe051-ac5e-521b-8770-3180fb0decb6"
C2 = "e9272fce-a569-5108-8def-0c35542cb640"
S1 = "26668f26-3e71-4dc6-8d3c-599e33425985"


def sample() -> dict:
    return {
        "id": S1,
        "subject": {"kind": "concept", "id": C1},
        "predicate": "part_of",
        "object": {"kind": "concept", "id": C2},
    }


def check(statements: list[dict], ids: list[str] | None = None) -> int:
    return verify_statement_ledger(
        statements,
        ids if ids is not None else [S1],
        concept_ids={C1, C2},
        predicate_slugs={"part_of"},
        expected_count=1,
    )


def test_committed_663_statement_uuids_preserved() -> None:
    assert verify_imported_statements(ROOT) == 663


def test_new_statements_are_allowed_without_changing_original_uuid() -> None:
    extra = deepcopy(sample())
    extra["id"] = str(uuid4())
    assert check([sample(), extra]) == 1


def test_missing_legacy_uuid_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing imported"):
        check([])


def test_rekeyed_legacy_statement_is_rejected() -> None:
    changed = deepcopy(sample())
    changed["id"] = str(uuid4())
    with pytest.raises(ValueError, match="missing imported"):
        check([changed])


def test_duplicate_statement_uuid_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate statement"):
        check([sample(), sample()])


def test_dangling_concept_or_statement_reference_is_rejected() -> None:
    changed = deepcopy(sample())
    changed["object"]["id"] = str(uuid4())
    with pytest.raises(ValueError, match="dangling concept"):
        check([changed])
    changed["object"] = {"kind": "statement", "id": str(uuid4())}
    with pytest.raises(ValueError, match="dangling statement"):
        check([changed])


def test_unknown_predicate_is_rejected() -> None:
    changed = deepcopy(sample())
    changed["predicate"] = "unknown"
    with pytest.raises(ValueError, match="unknown predicate"):
        check([changed])


def test_duplicate_or_short_legacy_ledger_is_rejected() -> None:
    with pytest.raises(ValueError, match="ledger count"):
        check([sample()], [])
    with pytest.raises(ValueError, match="ledger count"):
        check([sample()], [S1, S1])


def test_literal_can_be_an_object_but_not_subject() -> None:
    row = deepcopy(sample())
    row["object"] = {"kind": "literal", "datatype": "string", "value": "sample"}
    assert check([row]) == 1
    row["subject"] = {"kind": "literal", "datatype": "string", "value": "invalid"}
    with pytest.raises(ValueError, match="literal cannot"):
        check([row])
