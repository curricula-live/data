from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
SCHEMA = ROOT / "schema" / "knowledge"

FILES = {
    "concepts": KNOWLEDGE / "concepts.jsonl",
    "predicates": KNOWLEDGE / "predicates.jsonl",
    "statements": KNOWLEDGE / "statements.jsonl",
    "definitions": KNOWLEDGE / "definitions.jsonl",
}

SCHEMAS = {
    "concepts": SCHEMA / "concept.schema.json",
    "predicates": SCHEMA / "predicate.schema.json",
    "statements": SCHEMA / "statement.schema.json",
    "definitions": SCHEMA / "definition.schema.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        raise SystemExit(f"missing canonical file: {path.relative_to(ROOT)}")

    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path.relative_to(ROOT)}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{path.relative_to(ROOT)}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def validate_schema(name: str, rows: list[dict[str, Any]]) -> None:
    schema = load_json(SCHEMAS[name])
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for index, row in enumerate(rows, start=1):
        errors = sorted(validator.iter_errors(row), key=lambda error: list(error.path))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise SystemExit(f"{FILES[name].relative_to(ROOT)}:{index}: {details}")


def require_unique(values: list[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise SystemExit(f"duplicate {label}: {value}")
        seen.add(value)


def require_sorted(rows: list[dict[str, Any]], key: str, label: str) -> None:
    values = [str(row[key]) for row in rows]
    if values != sorted(values):
        raise SystemExit(f"{label} must be sorted by {key}")


def validate_references(
    concepts: list[dict[str, Any]],
    predicates: list[dict[str, Any]],
    statements: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
) -> None:
    concept_ids = {row["id"] for row in concepts}
    predicate_slugs = {row["slug"] for row in predicates}
    statement_ids = {row["id"] for row in statements}

    for row in statements:
        if row["predicate"] not in predicate_slugs:
            raise SystemExit(f"statement {row['id']} references unknown predicate {row['predicate']}")

        for side in ("subject", "object"):
            ref = row[side]
            kind = ref["kind"]
            if kind == "concept" and ref["id"] not in concept_ids:
                raise SystemExit(f"statement {row['id']} references unknown concept {ref['id']}")
            if kind == "statement" and ref["id"] not in statement_ids:
                raise SystemExit(f"statement {row['id']} references unknown statement {ref['id']}")

    defined_concepts: set[str] = set()
    for row in definitions:
        concept_id = row["concept_id"]
        if concept_id in defined_concepts:
            raise SystemExit(f"multiple canonical definitions for concept {concept_id}")
        defined_concepts.add(concept_id)

        if concept_id not in concept_ids:
            raise SystemExit(f"definition references unknown concept {concept_id}")
        for statement_id in row["statement_ids"]:
            if statement_id not in statement_ids:
                raise SystemExit(f"definition for {concept_id} references unknown statement {statement_id}")


def validate_semantic_admissions(rows: dict[str, list[dict[str, Any]]]) -> None:
    """Fail closed for any newly admitted source-qualified scientific statement."""
    admissions_path = KNOWLEDGE / "statement-admissions.jsonl"
    policies_path = KNOWLEDGE / "predicate-policies.jsonl"
    if not admissions_path.exists() and not policies_path.exists():
        return
    if not admissions_path.exists() or not policies_path.exists():
        raise SystemExit("semantic admission ledger and predicate policy must be committed together")
    admissions = load_jsonl(admissions_path)
    policies = load_jsonl(policies_path)
    require_unique([r["statement_id"] for r in admissions], "admission statement UUID")
    require_unique([r["slug"] for r in policies], "admission predicate policy")
    require_sorted(admissions, "statement_id", "knowledge/statement-admissions.jsonl")
    require_sorted(policies, "slug", "knowledge/predicate-policies.jsonl")
    statement_by_id = {r["id"]: r for r in rows["statements"]}
    predicate_by_slug = {r["slug"]: r for r in rows["predicates"]}
    concept_by_id = {r["id"]: r for r in rows["concepts"]}
    approved_policies = {}
    for policy in policies:
        slug = policy["slug"]
        if slug not in predicate_by_slug or policy["label"] != predicate_by_slug[slug]["label"]:
            raise SystemExit(f"missing or mismatched admitted predicate: {slug}")
        if not policy.get("semantics") or not policy.get("semantic_scope"):
            raise SystemExit(f"admitted predicate lacks a defined semantic scope: {slug}")
        for flag in ("transitive", "symmetric", "safe_for_subtype_inference",
                     "safe_for_prerequisite_inference", "safe_for_formal_proof"):
            if policy.get(flag) is not False:
                raise SystemExit(f"admitted predicate is not proof-safe: {slug} {flag}")
        translation_path = ROOT / "pipeline/semantic-admission/reviewed-predicate-logical-translations.json"
        reviewed_translations = load_json(translation_path)
        if policy.get("logical_translation") != reviewed_translations.get(slug):
            raise SystemExit(f"admitted predicate logical translation differs from review: {slug}")
        approved_policies[slug] = policy
    witnessed = set()
    for admission in admissions:
        sid = admission["statement_id"]
        stmt = statement_by_id.get(sid)
        if stmt is None or stmt["predicate"] not in approved_policies:
            raise SystemExit(f"admission {sid} missing a corresponding typed statement")
        if admission["predicate_slug"] != stmt["predicate"]:
            raise SystemExit(f"admission {sid} predicate differs from admitted statement")
        if admission.get("native_predicate") in ("subtype_of", "prerequisite_of"):
            raise SystemExit(f"source predicate was silently converted to canonical proof premise: {sid}")
        source = admission["source_id"]
        if source not in ("cso@3.5", "curricula-historical-v1@1.0.0"):
            raise SystemExit(f"unknown source in admission {sid}")
        if source == "cso@3.5" and (
            admission["native_predicate"] != "http://cso.kmi.open.ac.uk/schema/cso#superTopicOf"
            or stmt["predicate"] != "research_topic_parent_of"
        ):
            raise SystemExit(f"CSO predicate semantics invalid: {sid}")
        if source != "cso@3.5" and stmt["predicate"] == "research_topic_parent_of":
            raise SystemExit(f"archived V1 taxonomy may not be admitted: {sid}")
        if admission.get("review_level") not in (
            "editorially_screened_source_attested", "editorially_corrob_with_external_reference"
        ):
            raise SystemExit(f"unknown review tier: {sid}")
        for flag in ("inference_eligible", "proof_eligible", "independent_expert_review"):
            if admission.get(flag) is not False:
                raise SystemExit(f"unsupported scientific verification claim: {sid} {flag}")
        urls = admission.get("evidence_urls")
        if not isinstance(urls, list) or not urls or any(
            not isinstance(url, str) or not url.startswith("https://") for url in urls
        ):
            raise SystemExit(f"admission {sid} missing source evidence")
        if not admission.get("source_assertion_witness") or not admission.get("source_archive_sha256"):
            raise SystemExit(f"admission {sid} missing reproducible source provenance")
        if (stmt["subject"]["kind"], stmt["object"]["kind"]) != ("concept", "concept"):
            raise SystemExit(f"only concept-to-concept direct admissions supported: {sid}")
        for endpoint in ("subject", "object"):
            concept = concept_by_id.get(stmt[endpoint]["id"])
            reviewed_label = admission.get(endpoint + "_label")
            if (concept is None or not isinstance(reviewed_label, str)
                    or concept["label"].casefold() != reviewed_label.casefold()):
                raise SystemExit(f"admission {sid} endpoint differs from reviewed identity: {endpoint}")
        if source == "cso@3.5":
            subject_uri = admission.get("subject_source_uri")
            object_uri = admission.get("object_source_uri")
            if not isinstance(subject_uri, str) or not isinstance(object_uri, str):
                raise SystemExit(f"admission {sid} missing original CSO endpoints")
            triple = f'<{subject_uri}> <{admission["native_predicate"]}> <{object_uri}> .'
            expected = "sha256:" + hashlib.sha256(triple.encode("utf-8")).hexdigest()
            if admission["source_assertion_witness"] != expected:
                raise SystemExit(f"admission {sid} source witness differs from original triple")
        witness = (source, admission["source_assertion_witness"])
        if witness in witnessed:
            raise SystemExit(f"source assertion promoted twice: {witness}")
        witnessed.add(witness)
    manifest_path = ROOT / "pipeline/semantic-admission/admission-manifest.json"
    if not manifest_path.exists():
        raise SystemExit("semantic admission batch lacks the source review manifest")
    manifest = load_json(manifest_path)
    if (
        len(admissions) != manifest.get("new_statements")
        or len(policies) != manifest.get("new_predicates")
        or sum(a["source_id"] == "cso@3.5" for a in admissions)
            != manifest.get("source_cso_topic_relations")
        or sum(a["source_id"] == "curricula-historical-v1@1.0.0" for a in admissions)
            != manifest.get("externally_corrob_historical_core")
    ):
        raise SystemExit("semantic admission counts differ from the reviewed batch manifest")
    ledger_ids = {r["statement_id"] for r in admissions}
    unsafe = [s["id"] for s in rows["statements"]
              if s["predicate"] in approved_policies and s["id"] not in ledger_ids]
    if unsafe:
        raise SystemExit(f"unattested source-qualified canonical statements: {unsafe[:5]}")


def main() -> None:
    rows = {name: load_jsonl(path) for name, path in FILES.items()}

    for name, records in rows.items():
        validate_schema(name, records)

    require_unique([row["id"] for row in rows["concepts"]], "concept UUID")
    require_unique([row["slug"] for row in rows["concepts"]], "concept slug")
    require_unique([row["slug"] for row in rows["predicates"]], "predicate slug")
    require_unique([row["id"] for row in rows["statements"]], "statement UUID")

    require_sorted(rows["concepts"], "slug", "knowledge/concepts.jsonl")
    require_sorted(rows["predicates"], "slug", "knowledge/predicates.jsonl")
    require_sorted(rows["statements"], "id", "knowledge/statements.jsonl")
    require_sorted(rows["definitions"], "concept_id", "knowledge/definitions.jsonl")

    validate_references(
        rows["concepts"],
        rows["predicates"],
        rows["statements"],
        rows["definitions"],
    )

    validate_semantic_admissions(rows)

    print(
        "validated v2 knowledge: "
        f"{len(rows['concepts'])} concepts, "
        f"{len(rows['predicates'])} predicates, "
        f"{len(rows['statements'])} statements, "
        f"{len(rows['definitions'])} definitions"
    )


if __name__ == "__main__":
    main()
