"""Role signature sort checking is explicit and nonpublishing."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from scripts.validate_formal_roles import (
    ROOT, RoleSignatureError, validate_role_signatures, validate_quantified_class_model,
)

MANIFEST = ROOT / "tests/fixtures/role-signatures.synthetic.json"
MODEL = ROOT / "tests/fixtures/formal-array.synthetic.json"


def sample():
    return (json.loads(MODEL.read_text(encoding="utf-8")),
            json.loads(MANIFEST.read_text(encoding="utf-8")))


def test_real_registry_and_synthetic_object_role_are_only_syntactically_valid():
    model, manifest = sample()
    result = validate_quantified_class_model(model, manifest)
    assert result["valid"] is True
    assert result["typed_role_signatures_verified"] is True
    assert result["role_semantics_verified"] is False
    assert result["source_evidence_proves_quantifier"] is False
    assert result["may_publish"] is False
    assert result["quantified_role_occurrences"] == [
        {
            "operator": "some", "property_slug": "uses",
            "role_sort": "object_role", "scope": "synthetic_abstract_programming",
            "interpretation_source_verified": False,
        }
    ]


def test_universal_quantifier_requires_typed_role_and_does_not_infer_it():
    model, manifest = sample()
    model["expression"]["args"][1]["op"] = "only"
    result = validate_quantified_class_model(model, manifest)
    assert result["operator_counts"]["only"] == 1
    assert result["source_evidence_proves_quantifier"] is False


@pytest.mark.parametrize("alter", [
    lambda m, r: r.update({"scope": "scientific"}),
    lambda m, r: r["provenance"].update({"role_semantics_origin": "from_source"}),
    lambda m, r: r["provenance"].update({"status": "approved"}),
    lambda m, r: r["snapshot"].update({"concepts_sha256": "sha256:" + "0"*64}),
    lambda m, r: r["snapshot"].update({"predicates_sha256": "sha256:" + "f"*64}),
    lambda m, r: r["signatures"].append(deepcopy(r["signatures"][0])),
    lambda m, r: r["signatures"][0].update({"role_sort": "data_role"}),
    lambda m, r: r["signatures"][0].update({"property_slug": "invented_role"}),
    lambda m, r: r["signatures"][0].update({"domain_concept_id": "00000000-0000-4000-8000-000000000000"}),
    lambda m, r: r["signatures"][0].update({"range_concept_id": "00000000-0000-4000-8000-000000000000"}),
    lambda m, r: r["signatures"][0].update({"claims_scientific_truth": True}),
    lambda m, r: m.update({"scope": "synthetic_other"}),
    lambda m, r: m["expression"]["args"][1].update({"property": "measures"}),
    lambda m, r: m["expression"]["args"][1].update({"op": "forall"}),
])
def test_bad_sort_scope_or_unadmitted_role_fails_closed(alter):
    model, manifest = sample()
    alter(model, manifest)
    with pytest.raises(RoleSignatureError):
        validate_quantified_class_model(model, manifest)


def test_registry_drift_is_detected_by_hash_even_when_role_name_exists():
    _, manifest = sample()
    original = (ROOT / "knowledge/predicates.jsonl").read_bytes()
    with pytest.raises(RoleSignatureError, match="Stale or mismatched"):
        validate_role_signatures(manifest, predicates_bytes=original + b"\n")


def test_synthetic_roles_never_mutate_canonical_knowledge():
    model, manifest = sample()
    paths = [
        ROOT / "knowledge/predicates.jsonl",
        ROOT / "knowledge/statements.jsonl",
        ROOT / "knowledge/definitions.jsonl",
    ]
    old = [p.read_bytes() for p in paths]
    validate_quantified_class_model(model, manifest)
    assert old == [p.read_bytes() for p in paths]
