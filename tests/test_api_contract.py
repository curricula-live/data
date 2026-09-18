import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "knowledge" / "concepts.jsonl"
PREDICATES = ROOT / "knowledge" / "predicates.jsonl"
STATEMENTS = ROOT / "knowledge" / "statements.jsonl"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_canonical_concepts_preserve_slug_lookup_contract():
    concepts = read_jsonl(CONCEPTS)

    assert concepts
    assert all(concept["id"] and concept["slug"] and concept["label"] for concept in concepts)
    assert len({concept["id"] for concept in concepts}) == len(concepts)
    assert len({concept["slug"] for concept in concepts}) == len(concepts)


def test_canonical_predicates_preserve_readable_relation_types():
    predicates = read_jsonl(PREDICATES)

    assert predicates
    assert all(predicate["slug"] and predicate["label"] for predicate in predicates)
    assert len({predicate["slug"] for predicate in predicates}) == len(predicates)


def test_migrated_statement_endpoints_resolve():
    concepts = {concept["id"] for concept in read_jsonl(CONCEPTS)}
    statements = read_jsonl(STATEMENTS)
    statement_ids = {statement["id"] for statement in statements}

    for statement in statements:
        for side in ("subject", "object"):
            reference = statement[side]
            if reference["kind"] == "concept":
                assert reference["id"] in concepts
            elif reference["kind"] == "statement":
                assert reference["id"] in statement_ids
