import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "data" / "concepts.jsonl"
RELATIONS = ROOT / "data" / "relations.jsonl"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_concept_snapshot_can_supply_read_api_identity():
    concepts = read_jsonl(CONCEPTS)

    assert concepts
    assert all(isinstance(concept["slug"], str) and concept["slug"] for concept in concepts)
    assert len({concept["slug"] for concept in concepts}) == len(concepts)


def test_relation_snapshot_can_supply_read_api_semantics():
    relations = read_jsonl(RELATIONS)

    assert all(
        isinstance(relation[field], str) and relation[field]
        for relation in relations
        for field in ("source", "type", "target")
    )


def test_relations_reference_snapshot_concepts():
    concepts = {concept["slug"] for concept in read_jsonl(CONCEPTS)}

    for relation in read_jsonl(RELATIONS):
        assert relation["source"] in concepts
        assert relation["target"] in concepts


def test_relation_semantic_identity_is_unique():
    semantic_keys = [
        (relation["source"], relation["type"], relation["target"])
        for relation in read_jsonl(RELATIONS)
    ]

    assert len(set(semantic_keys)) == len(semantic_keys)


def test_snapshot_order_matches_api_deterministic_order():
    concepts = read_jsonl(CONCEPTS)
    relations = read_jsonl(RELATIONS)

    assert concepts == sorted(concepts, key=lambda concept: concept["slug"])
    assert relations == sorted(
        relations,
        key=lambda relation: (relation["source"], relation["type"], relation["target"]),
    )


def test_prerequisite_relation_direction_is_canonical_when_present():
    """The contract is A --prerequisite_of--> B: A must be learned before B.

    The snapshot does not need to contain prerequisite edges yet; this guards the
    relation-type spelling consumed by the API traversal once such edges exist.
    """
    relation_types = {relation["type"] for relation in read_jsonl(RELATIONS)}
    prerequisite_spellings = {
        relation_type for relation_type in relation_types if "prereq" in relation_type
    }

    assert prerequisite_spellings <= {"prerequisite_of"}
