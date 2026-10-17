import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "knowledge"


def validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_concept_v2_is_minimal() -> None:
    concept = {
        "id": "11111111-1111-4111-8111-111111111111",
        "slug": "two-s-complement",
        "label": "Two's complement",
    }
    validator("concept.schema.json").validate(concept)


def test_concept_rejects_generic_description() -> None:
    concept = {
        "id": "11111111-1111-4111-8111-111111111111",
        "slug": "queue",
        "label": "Queue",
        "description": "Opaque prose should not be canonical concept data.",
    }
    with pytest.raises(ValidationError):
        validator("concept.schema.json").validate(concept)


def test_statement_can_reference_another_statement() -> None:
    statement = {
        "id": "33333333-3333-4333-8333-333333333333",
        "subject": {
            "kind": "statement",
            "id": "22222222-2222-4222-8222-222222222222",
        },
        "predicate": "qualifies",
        "object": {
            "kind": "concept",
            "id": "11111111-1111-4111-8111-111111111111",
        },
    }
    validator("statement.schema.json").validate(statement)


def test_definition_contains_statement_ids_not_prose() -> None:
    definition = {
        "concept_id": "11111111-1111-4111-8111-111111111111",
        "statement_ids": ["22222222-2222-4222-8222-222222222222"],
    }
    validator("definition.schema.json").validate(definition)

    with pytest.raises(ValidationError):
        validator("definition.schema.json").validate({**definition, "text": "A queue is ..."})
