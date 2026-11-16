"""Inspect canonical concept/statement coverage and create NON-PUBLISHABLE review dossiers.

Usage:
    python scripts/knowledge_review_queue.py --format markdown
    python scripts/knowledge_review_queue.py --format json --output /tmp/concept-review.json

This command reads files in curricula-live/data and produces reports ONLY.
It never imports ontology snapshots, mutates canonical JSONL or contacts databases.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "pipeline" / "concept-review-priorities.json"
PREDICATE_NOTE = {
    "subtype_of": "Candidate transitive classification; prove source and conceptual context before use",
    "part_of": "Part/whole semantics can differ by entity kind; no general transitivity assumed",
    "uses": "Broad dependency or operational use; never infer prerequisite, access method or type",
    "related_to": "Underspecified association; no logical consequences authorized",
    "prerequisite_of": "Educational prerequisites require learner context and reviewed evidence",
    "implemented_by": "Implementation relation must specify representation and implementation context",
    "represents": "Separate denotation/encoding/data-model relations before deriving properties",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_report(root: Path = ROOT, config_path: Path | None = None) -> dict:
    config = json.loads((config_path or root / "pipeline" / "concept-review-priorities.json").read_text(encoding="utf-8"))
    if config["status"] != "proposal_only_not_approved":
        raise ValueError("This report only accepts a non-publishable proposal queue")

    concepts = read_jsonl(root / "knowledge" / "concepts.jsonl")
    statements = read_jsonl(root / "knowledge" / "statements.jsonl")
    predicates = read_jsonl(root / "knowledge" / "predicates.jsonl")
    definitions = read_jsonl(root / "knowledge" / "definitions.jsonl")
    by_slug = {c["slug"]: c for c in concepts}
    by_id = {c["id"]: c for c in concepts}
    if len(by_slug) != len(concepts) or len(by_id) != len(concepts):
        raise ValueError("Canonical concepts contain duplicate identities")
    known_predicates = {p["slug"] for p in predicates}

    by_concept: dict[str, list[dict]] = defaultdict(list)
    counts = Counter()
    for row in statements:
        predicate = row["predicate"]
        if predicate not in known_predicates:
            raise ValueError("Statement references an unknown predicate: " + predicate)
        counts[predicate] += 1
        for side in ("subject", "object"):
            ref = row[side]
            if ref["kind"] != "concept":
                continue
            if ref["id"] not in by_id:
                raise ValueError("Statement references an unknown concept identity")
            by_concept[ref["id"]].append(row)

    proposed = []
    seen = set()
    for item in config["priorities"]:
        slug = item["slug"]
        if slug in seen:
            raise ValueError("Duplicate concept in priority queue: " + slug)
        seen.add(slug)
        concept = by_slug.get(slug)
        related = by_concept.get(concept["id"], []) if concept else []
        types = Counter(statement["predicate"] for statement in related)
        definition = any(
            d.get("concept") == concept["id"] or d.get("concept_id") == concept["id"]
            for d in definitions
        ) if concept else False
        def describe_ref(ref: dict) -> str:
            if ref["kind"] == "concept":
                return by_id[ref["id"]]["slug"]
            if ref["kind"] == "statement":
                return "statement:" + ref["id"]
            return "literal:" + ref.get("datatype", "unknown") + ":" + str(ref.get("value", ""))

        recorded_statements = [
            {
                "id": statement["id"],
                "subject": describe_ref(statement["subject"]),
                "predicate": statement["predicate"],
                "object": describe_ref(statement["object"]),
                "source_verification": "not_established_by_core_statement_record",
                "review_status": "pending",
            }
            for statement in sorted(related, key=lambda row: row["id"])
        ]
        proposed.append({
            "tier": item["tier"],
            "slug": slug,
            "canonical_concept_id": concept["id"] if concept else None,
            "canonical_presence": "present" if concept else "missing",
            "direct_statement_count": len(related),
            "recorded_statements": recorded_statements,
            "statement_predicates": dict(sorted(types.items())),
            "canonical_definition_present": definition,
            "source_admission": "not_established_by_this_report",
            "scientific_claim_review": "pending",
            "identity_mapping_review": "pending",
            "status": "review_candidate_only",
            "reason": item["reason"],
        })

    predicate_audit = [
        {
            "predicate": p["slug"],
            "statement_count": counts[p["slug"]],
            "semantic_review_status": "pending",
            "logical_rules_authorized": [],
            "notes": PREDICATE_NOTE.get(
                p["slug"], "Requires explicit domain, range, inverse and contextual semantics review"
            ),
        }
        for p in sorted(predicates, key=lambda p: p["slug"])
    ]
    return {
        "schema_version": "concept-review-dossier@1",
        "authorizes_import": False,
        "authorizes_publication": False,
        "origin": "canonical_data_repository_read_only",
        "current_corpus": {
            "concepts": len(concepts),
            "statements": len(statements),
            "predicates": len(predicates),
            "definitions": len(definitions),
        },
        "required_gates": config["required_gates"],
        "priority_queue": proposed,
        "predicate_audit": predicate_audit,
    }


def to_markdown(report: dict, detail_slug: str | None = None) -> str:
    corpus = report["current_corpus"]
    lines = [
        "# Non-canonical concept review queue",
        "",
        "This is a review plan, **not approved claims or permission to import/publish**.",
        "",
        f"Current corpus: {corpus['concepts']} concepts · {corpus['statements']} statements · "
        f"{corpus['predicates']} predicates · {corpus['definitions']} definitions.",
        "",
        "| Tier | Concept | Existing statements | Definition | Review |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in report["priority_queue"]:
        lines.append(
            f"| {row['tier']} | {row['slug']} | {row['direct_statement_count']} | "
            f"{'present' if row['canonical_definition_present'] else 'absent'} | "
            f"{'existing canonical identity' if row['canonical_concept_id'] else 'identity mapping required'} |"
        )
    if detail_slug:
        selection = next((row for row in report["priority_queue"] if row["slug"] == detail_slug), None)
        if selection is None:
            raise ValueError("Concept not found in prioritized review queue: " + detail_slug)
        lines += [
            "",
            "## Recorded statements to review: " + detail_slug,
            "",
            "Every line below is an *existing assertion* (not newly proposed source truth).",
            "",
            "| Source UUID | Subject | Predicate | Object |",
            "| --- | --- | --- | --- |",
        ]
        for assertion in selection["recorded_statements"]:
            lines.append(
                f"| `{assertion['id']}` | {assertion['subject']} | "
                f"{assertion['predicate']} | {assertion['object']} |"
            )
        lines += [
            "",
            "Identity, predicate semantics, evidence and logical scope remain unreviewed.",
        ]

    lines += [
        "",
        "## Predicate semantics still to be reviewed",
        "",
        "| Predicate | Assertions | Unverified rule concern |",
        "| --- | ---: | --- |",
    ]
    for row in report["predicate_audit"]:
        lines.append(f"| {row['predicate']} | {row['statement_count']} | {row['notes']} |")
    lines += [
        "",
        "## Admission gates",
        "",
        " → ".join(report["required_gates"]),
        "",
        "No inference rule or publication permission is granted by this report.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", type=Path, help="Report destination (defaults to stdout)")
    parser.add_argument("--concept", help="Append all recorded claims for one priority concept")
    args = parser.parse_args()
    report = build_report()
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else to_markdown(report, args.concept)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
