"""Experimental, read-only role-signature validation and typed quantifier checking.

A recorded concept-to-concept 'uses' assertion does NOT license
an individual-role interpretation or a universal/existential restriction.
Each role interpretation is an explicit hypothetical declaration. No
canonical knowledge or runtime PostgreSQL table is mutated.

Usage:
  python scripts/validate_formal_roles.py tests/fixtures/role-signatures.synthetic.json \
    --model tests/fixtures/formal-array.synthetic.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

if __package__:
    from .validate_formal_class_model import ROOT, validate_model, ModelValidationError
else:
    from validate_formal_class_model import ROOT, validate_model, ModelValidationError

SCHEMA = ROOT / "schema/knowledge/formal-role-signatures.v0.schema.json"


class RoleSignatureError(ValueError):
    pass


def _jsonl_ids(content: bytes, key: str) -> set[str]:
    try:
        rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise RoleSignatureError("Invalid canonical registry JSONL") from exc
    ids = {row[key] for row in rows}
    if len(ids) != len(rows):
        raise RoleSignatureError("Duplicate canonical registry identifier")
    return ids


def validate_role_signatures(
    manifest: dict,
    *,
    concepts_bytes: bytes | None = None,
    predicates_bytes: bytes | None = None,
) -> dict:
    validator = Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=FormatChecker()
    )
    errors = sorted(validator.iter_errors(manifest), key=lambda error: str(list(error.absolute_path)))
    if errors:
        err = errors[0]
        raise RoleSignatureError(f"Invalid typed roles at {list(err.absolute_path)}: {err.message}")

    if concepts_bytes is None:
        concepts_bytes = (ROOT / "knowledge/concepts.jsonl").read_bytes()
    if predicates_bytes is None:
        predicates_bytes = (ROOT / "knowledge/predicates.jsonl").read_bytes()
    for label, content in (("concepts", concepts_bytes), ("predicates", predicates_bytes)):
        expected = "sha256:" + sha256(content).hexdigest()
        if manifest["snapshot"][f"{label}_sha256"] != expected:
            raise RoleSignatureError(f"Stale or mismatched {label} snapshot")

    concept_ids = _jsonl_ids(concepts_bytes, "id")
    predicate_slugs = _jsonl_ids(predicates_bytes, "slug")
    seen: set[str] = set()
    for signature in manifest["signatures"]:
        name = signature["property_slug"]
        if name in seen:
            raise RoleSignatureError(f"Duplicate property declaration: {name}")
        seen.add(name)
        if name not in predicate_slugs:
            raise RoleSignatureError(f"Unknown canonical predicate: {name}")
        for key in ("domain_concept_id", "range_concept_id"):
            value = signature[key]
            if value is not None and value not in concept_ids:
                raise RoleSignatureError(f"Unknown {key} in {name}")
        if signature["role_sort"] == "data_role" and signature["range_concept_id"] is not None:
            raise RoleSignatureError("Literal-valued data roles cannot declare a class range")
    return {
        "schema_version": manifest["schema_version"],
        "scope": manifest["scope"],
        "role_count": len(seen),
        "role_sorts": {
            name: next(s["role_sort"] for s in manifest["signatures"]
                       if s["property_slug"] == name)
            for name in sorted(seen)
        },
        "canonical_predicate_identity_checked": True,
        "semantic_role_interpretation_verified": False,
        "scope_origin": "assumed_not_in_source",
        "may_publish": False,
    }


def validate_quantified_class_model(
    model: dict,
    manifest: dict,
    *,
    concepts_bytes: bytes | None = None,
    predicates_bytes: bytes | None = None,
) -> dict:
    report = validate_role_signatures(
        manifest, concepts_bytes=concepts_bytes, predicates_bytes=predicates_bytes
    )
    if model.get("scope") != report["scope"]:
        raise RoleSignatureError("Model and role semantics must have the same hypothetical scope")
    # The pre-existing model validator checks all concept UUIDs, registered
    # predicate slugs, bounded AST recursion, and the synthetic-only status.
    if concepts_bytes is None:
        concepts_bytes = (ROOT / "knowledge/concepts.jsonl").read_bytes()
    if predicates_bytes is None:
        predicates_bytes = (ROOT / "knowledge/predicates.jsonl").read_bytes()
    try:
        checked = validate_model(
            model,
            concept_ids=_jsonl_ids(concepts_bytes, "id"),
            predicate_slugs=_jsonl_ids(predicates_bytes, "slug"),
        )
    except ModelValidationError as exc:
        raise RoleSignatureError(f"Invalid class expression: {exc}") from exc
    signatures = {s["property_slug"]: s for s in manifest["signatures"]}
    quantifiers: list[dict] = []

    def walk(expr: dict) -> None:
        op = expr["op"]
        if op in ("some", "only"):
            property_name = expr["property"]
            signature = signatures.get(property_name)
            if signature is None:
                raise RoleSignatureError(f"No typed role declaration for {property_name}")
            if signature["role_sort"] != "object_role":
                raise RoleSignatureError(
                    f"Cannot quantify over class filler using literal-valued role {property_name}"
                )
            quantifiers.append({
                "operator": op,
                "property_slug": property_name,
                "role_sort": signature["role_sort"],
                "scope": report["scope"],
                "interpretation_source_verified": False,
            })
            walk(expr["filler"])
        elif op in ("and", "or"):
            for arg in expr["args"]:
                walk(arg)
        elif op == "not":
            walk(expr["arg"])

    walk(model["expression"])
    return {
        **checked,
        "typed_role_signatures_verified": True,
        "role_semantics_verified": False,
        "quantified_role_occurrences": quantifiers,
        "source_evidence_proves_quantifier": False,
        "may_publish": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role_manifest", type=Path)
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.role_manifest.read_text(encoding="utf-8"))
    if args.model:
        model = json.loads(args.model.read_text(encoding="utf-8"))
        result = validate_quantified_class_model(model, manifest)
    else:
        result = validate_role_signatures(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
