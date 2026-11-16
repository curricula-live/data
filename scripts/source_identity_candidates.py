"""Prepare NONPUBLISHABLE source identity candidates for canonical-data review.

This tool consumes a manifest of externally obtained, explicitly versioned
source NODE identities. It does not consume or import source assertions.
Lexical name matches are NEVER treated as verified identity alignments.

Usage:
  python scripts/source_identity_candidates.py --input /tmp/source-nodes.jsonl
  python scripts/source_identity_candidates.py --input /tmp/source-nodes.jsonl --format json

The ontology V2 federation still needs a real source-admitted, rights-cleared
export. Archived V1 content is NOT a supported import input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

ALLOWED = {
    "source_id", "source_version", "source_uri", "label",
    "source_checksum_sha256", "source_locator", "rights_status",
    "candidate_slug",
}
FORBIDDEN_RELATION_KEYS = {
    "subject", "predicate", "object", "target", "triples", "edges", "assertions",
}


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.strip().lower())).strip("-")


def _identity_key(record: dict) -> tuple[str, str, str]:
    return record["source_id"], record["source_version"], record["source_uri"]


def _validate_record(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("Each source candidate must be an object")
    if set(record) & FORBIDDEN_RELATION_KEYS:
        raise ValueError("Source assertions/relations are forbidden in identity discovery manifests")
    unknown = set(record) - ALLOWED
    if unknown:
        raise ValueError("Unrecognized source manifest fields: " + ", ".join(sorted(unknown)))
    required = {"source_id", "source_version", "source_uri", "label"}
    if not all(isinstance(record.get(key), str) and record[key].strip() for key in required):
        raise ValueError("Missing source identity/version/URI/label metadata")
    url = urlparse(record["source_uri"])
    if url.scheme not in ("https", "http") or not url.netloc or url.username or url.password:
        raise ValueError("Invalid absolute source URI")
    if record.get("source_checksum_sha256") is not None and not re.fullmatch(
        r"[a-fA-F0-9]{64}", record["source_checksum_sha256"]
    ):
        raise ValueError("Expected source checksum as 64 hexadecimal characters")
    if record.get("candidate_slug") is not None and not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", record["candidate_slug"]
    ):
        raise ValueError("Candidate slug is not a canonical slug")
    if record.get("rights_status", "unverified") not in {
        "unverified", "rights_review_requested", "license_evidence_attached",
    }:
        raise ValueError("Rights must be unverified/pending; this tool cannot certify licenses")


def build_candidates(input_path: Path, root: Path = ROOT) -> dict:
    records = _jsonl(input_path)
    identities = _jsonl(root / "knowledge" / "concepts.jsonl")
    queue = json.loads((root / "pipeline/concept-review-priorities.json").read_text(encoding="utf-8"))
    by_slug = {row["slug"]: row["id"] for row in identities}
    tier_by_slug = {row["slug"]: row["tier"] for row in queue["priorities"]}
    if len(by_slug) != len(identities):
        raise ValueError("Canonical concept identity registry has duplicate slugs")
    seen: set[tuple[str, str, str]] = set()
    candidates: list[dict] = []

    for record in records:
        _validate_record(record)
        key = _identity_key(record)
        if key in seen:
            raise ValueError("Repeated native source URI within the same source and version")
        seen.add(key)
        explicit = record.get("candidate_slug")
        lexical = _slugify(record["label"])
        suggestions = []
        for slug in dict.fromkeys((explicit, lexical)):
            if slug and slug in by_slug:
                suggestions.append({
                    "canonical_slug": slug,
                    "canonical_concept_id": by_slug[slug],
                    "suggestion_basis": "reviewer_proposed_slug" if slug == explicit else "lexical_label_only",
                    "identity_verified": False,
                    "alignment_decision": "not_established",
                })
        tier = min(
            (tier_by_slug[row["canonical_slug"]] for row in suggestions
             if row["canonical_slug"] in tier_by_slug),
            default="not_prioritized",
            key=lambda name: {
                "core": 0, "supporting": 1, "candidate_not_currently_canonical": 2,
                "defer_unless_needed": 3, "not_prioritized": 4,
            }.get(name, 4),
        )
        candidates.append({
            "source_id": record["source_id"],
            "source_version": record["source_version"],
            "source_uri": record["source_uri"],
            "label": record["label"],
            "source_checksum_sha256": record.get("source_checksum_sha256"),
            "source_locator": record.get("source_locator"),
            "supplied_rights_status": record.get("rights_status", "unverified"),
            "rights_independently_verified": False,
            "candidates": suggestions,
            "review_tier": tier,
            "semantic_identity_status": "unreviewed",
            "may_publish": False,
            "may_import_assertions": False,
        })
    candidates.sort(key=lambda row: (row["source_id"], row["source_version"], row["source_uri"]))
    return {
        "schema_version": "source-identity-candidates@1",
        "origin": "source_discovery_manifest_unverified",
        "record_count": len(candidates),
        "authorizes_ontology_admission": False,
        "authorizes_canonical_mutation": False,
        "authorizes_publication": False,
        "note": (
            "Lexical candidate similarity is not entity identity; current ontology "
            "V2 source corpus has not been admitted. Human source, rights, identity "
            "and semantics review is required for each suggestion."
        ),
        "records": candidates,
    }


def to_markdown(report: dict) -> str:
    lines = [
        "# Proposed source identity crosswalk (unreviewed)",
        "",
        report["note"],
        "",
        "| Native URI | Label | Candidate UUID/slug | Tier |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["records"]:
        guesses = ", ".join(
            "`" + row["canonical_slug"] + "` / `" + row["canonical_concept_id"] + "`"
            for row in item["candidates"]
        ) or "unresolved"
        lines.append(
            f"| `{item['source_uri']}` | {item['label']} | {guesses} | {item['review_tier']} |"
        )
    lines += [
        "",
        "All matches are candidate suggestions. Source/rights/semantic identity"
        " gates are unreviewed; no assertions are imported or published.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Versioned V2 source-node discovery JSONL")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path, help="Optional report destination")
    args = parser.parse_args()
    report = build_candidates(args.input)
    result = json.dumps(report, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else to_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
