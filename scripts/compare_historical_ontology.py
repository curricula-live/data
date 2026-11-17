"""Compare canonical data with the HISTORICAL native ontology, without importing it.

Read-only, deterministic, generic concept evidence audit. This is a
comparison of two different repositories and modeling scopes: lexical slug
matches are NOT approved concept-identity crosswalks; broader_topic is NOT
assumed equivalent to subtype_of; old formal grammar statements are NOT
reviewed scientific facts.

Example (from curricula-live/data checkout, with sibling ontology clone):
  python scripts/compare_historical_ontology.py \
    --historical-native ../ontology/native-v2 \
    --concept algorithm --concept computer-network --format markdown

The report does not alter canonical JSONL, write to a database, generate
concept-specific Markdown files, or promote imported source claims.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAL_PREFIX = "formal_"
MAX_EXAMPLES = 20


class ComparisonError(ValueError):
    pass


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise ComparisonError(f"Missing expected source file: {path}")
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise ComparisonError(f"Invalid JSONL in {path}") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise ComparisonError("Expected JSON objects in " + str(path))
    return rows


def _unique(records: list[dict], field: str, context: str) -> dict:
    result = {row[field]: row for row in records}
    if len(result) != len(records):
        raise ComparisonError(f"Duplicate {field} in {context}")
    return result


def _all_concept_edges(
    statements: list[dict],
    concepts: dict[str, dict],
) -> tuple[dict[str, list[dict]], dict[str, list[dict]], Counter, Counter]:
    outgoing: dict[str, list[dict]] = defaultdict(list)
    incoming: dict[str, list[dict]] = defaultdict(list)
    kind_pairs: Counter = Counter()
    c2c_types: Counter = Counter()

    for stmt in statements:
        subject, obj = stmt["subject"], stmt["object"]
        subject_kind, object_kind = subject["kind"], obj["kind"]
        kind_pairs[f"{subject_kind}->{object_kind}"] += 1
        if subject_kind != "concept" or object_kind != "concept":
            continue
        start, end = subject["id"], obj["id"]
        if start not in concepts or end not in concepts:
            raise ComparisonError("Graph concept edge references missing identity")
        record = {
            "assertion_id": stmt["id"],
            "subject_id": start,
            "subject_label": concepts[start]["label"],
            "predicate": stmt["predicate"],
            "object_id": end,
            "object_label": concepts[end]["label"],
        }
        outgoing[start].append(record)
        incoming[end].append(record)
        c2c_types[stmt["predicate"]] += 1
    for group in (outgoing, incoming):
        for values in group.values():
            values.sort(key=lambda item: (
                item["predicate"], item["subject_label"], item["object_label"], item["assertion_id"]
            ))
    return outgoing, incoming, kind_pairs, c2c_types


def _formal_roots(
    concept_id: str,
    definitions: dict[str, dict],
    statements_by_id: dict[str, dict],
) -> dict:
    entry = definitions.get(concept_id)
    if not entry:
        return {"selected_statement_count": 0, "root_record_kinds": {}, "scopes": []}
    selected = entry["statement_ids"]
    kinds: Counter = Counter()
    scope: set[str] = set()
    for sid in selected:
        record = statements_by_id.get(sid)
        if record is None:
            raise ComparisonError("Selected native definition references missing statement")
        if record["subject"]["kind"] == "concept" and record["subject"]["id"] == concept_id:
            if record["predicate"] == "has_semantic_specification" and record["object"]["kind"] == "literal":
                kinds[str(record["object"]["value"])] += 1
        if record["predicate"] == "formal_scope" and record["object"]["kind"] == "literal":
            scope.add(str(record["object"]["value"]))
    return {
        "selected_statement_count": len(selected),
        "root_record_kinds": dict(sorted(kinds.items())),
        "scopes": sorted(scope)[:MAX_EXAMPLES],
    }


def build_comparison(
    data_root: Path,
    historical_native_root: Path,
    concept_slugs: list[str],
    *,
    example_limit: int = 12,
) -> dict[str, Any]:
    """Return an inspectable, never-publishable comparison for any concept slugs."""
    if not 1 <= example_limit <= MAX_EXAMPLES:
        raise ComparisonError("Example limit must be 1–20")
    if not concept_slugs or len(concept_slugs) > 20 or len(concept_slugs) != len(set(concept_slugs)):
        raise ComparisonError("Select 1–20 distinct concept slugs")

    manifest_path = historical_native_root / "manifest.json"
    if not manifest_path.is_file():
        raise ComparisonError("Missing historical release manifest; path must be native-v2")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("published") is not False or manifest.get("automaticPublicationAllowed") is not False:
        raise ComparisonError("This audit is restricted to the unpublished historical snapshot")

    current = data_root / "knowledge"
    historic = historical_native_root / "knowledge"
    data_concepts = read_jsonl(current / "concepts.jsonl")
    data_predicates = read_jsonl(current / "predicates.jsonl")
    data_statements = read_jsonl(current / "statements.jsonl")
    data_definitions = read_jsonl(current / "definitions.jsonl")
    native_concepts = read_jsonl(historic / "concepts.jsonl")
    native_predicates = read_jsonl(historic / "predicates.jsonl")
    native_statements = read_jsonl(historic / "statements.jsonl")
    native_definitions = read_jsonl(historic / "definitions.jsonl")

    d_ids = _unique(data_concepts, "id", "canonical concepts")
    h_ids = _unique(native_concepts, "id", "historic concepts")
    d_slugs = _unique(data_concepts, "slug", "canonical slugs")
    h_slugs = _unique(native_concepts, "slug", "historic slugs")
    d_out, d_in, d_kinds, d_types = _all_concept_edges(data_statements, d_ids)
    h_out, h_in, h_kinds, h_types = _all_concept_edges(native_statements, h_ids)
    h_definition_ids = _unique(native_definitions, "concept_id", "historic definitions")
    h_statements_by_id = _unique(native_statements, "id", "historic statements")

    formal_predicates = sorted(p["slug"] for p in native_predicates if p["slug"].startswith(FORMAL_PREFIX))
    # This count is a naming-based analysis, not a reviewed ontology-predicate taxonomy.
    nonformal_predicates = sorted(p["slug"] for p in native_predicates if not p["slug"].startswith(FORMAL_PREFIX))

    focus = []
    for slug in concept_slugs:
        canonical, historical = d_slugs.get(slug), h_slugs.get(slug)
        entry = {
            "requested_slug": slug,
            "lexical_slug_match_only": bool(canonical and historical),
            "identity_equivalence_verified": False,
            "canonical": None,
            "historical_native": None,
        }
        if canonical:
            cid = canonical["id"]
            entry["canonical"] = {
                "concept_id": cid,
                "label": canonical["label"],
                "incident_concept_edges": len(d_out[cid]) + len(d_in[cid]),
                "outgoing_count": len(d_out[cid]),
                "incoming_count": len(d_in[cid]),
                "outgoing": d_out[cid][:example_limit],
                "incoming": d_in[cid][:example_limit],
                "predicate_counts": dict(sorted(Counter(
                    x["predicate"] for x in d_out[cid] + d_in[cid]
                ).items())),
            }
        if historical:
            cid = historical["id"]
            entry["historical_native"] = {
                "concept_id": cid,
                "label": historical["label"],
                "incident_concept_edges": len(h_out[cid]) + len(h_in[cid]),
                "outgoing_count": len(h_out[cid]),
                "incoming_count": len(h_in[cid]),
                "outgoing": h_out[cid][:example_limit],
                "incoming": h_in[cid][:example_limit],
                "predicate_counts": dict(sorted(Counter(
                    x["predicate"] for x in h_out[cid] + h_in[cid]
                ).items())),
                "structured_record_summary": _formal_roots(cid, h_definition_ids, h_statements_by_id),
            }
        focus.append(entry)

    return {
        "schema_version": "historical-ontology-comparison.v0",
        "status": "read_only_nonpublishing",
        "identity_crosswalk_status": "not_verified_slug_comparison_only",
        "caution": (
            "Historic native ontology is archived and unpublished. 'broader_topic' "
            "is not a justified substitute for 'subtype_of'; formal_* predicate "
            "names predominantly encode grammar, not independent scientific facts."
        ),
        "historical_release": {
            "version": manifest.get("version"),
            "published": manifest["published"],
            "automatic_publication_allowed": manifest["automaticPublicationAllowed"],
        },
        "canonical_counts": {
            "concepts": len(data_concepts),
            "predicate_types": len(data_predicates),
            "statements": len(data_statements),
            "definitions": len(data_definitions),
            "concept_to_concept": sum(d_types.values()),
            "concept_relation_predicates": dict(sorted(d_types.items())),
        },
        "historical_counts": {
            "concepts": len(native_concepts),
            "predicate_types": len(native_predicates),
            "formal_prefix_predicates": len(formal_predicates),
            "other_predicates": len(nonformal_predicates),
            "statements": len(native_statements),
            "definitions": len(native_definitions),
            "concept_to_concept": sum(h_types.values()),
            "concept_relation_predicates": dict(sorted(h_types.items())),
            "endpoint_kind_counts": dict(sorted(h_kinds.items())),
        },
        "concepts": focus,
    }


def render_markdown(report: dict) -> str:
    d, h = report["canonical_counts"], report["historical_counts"]
    out = [
        "# Historical ontology vs canonical data — comparative diagnostics",
        "",
        "**Research-only comparison; nothing is imported, reviewed or published.**",
        "",
        "| Measure | Canonical data | Historical native ontology |",
        "|---|---:|---:|",
    ]
    for title, key in [
        ("Concepts", "concepts"), ("Predicate types", "predicate_types"),
        ("Statements (all kinds)", "statements"),
        ("Concept-to-concept relations", "concept_to_concept"),
        ("Selected definition structures", "definitions"),
    ]:
        out.append(f"| {title} | {d[key]:,} | {h[key]:,} |")
    out += [
        "",
        f"Historical predicates prefixed `formal_`: **{h['formal_prefix_predicates']}**; "
        f"others: **{h['other_predicates']}**.",
        "Historical concept-to-concept predicates: " + ", ".join(
            f"`{key}` ({value})"
            for key, value in h["concept_relation_predicates"].items()
        ) + ".",
        "",
    ]
    for entry in report["concepts"]:
        out.append(f"## {entry['requested_slug']}")
        drow, hrow = entry["canonical"], entry["historical_native"]
        if not drow or not hrow:
            out.append("Not an exact slug match across both sources; manual identity reconciliation required.")
            out.append("")
            continue
        out.extend([
            f"Canonical: **{drow['incident_concept_edges']}** incident directed relations "
            f"({drow['outgoing_count']} outgoing). "
            f"Historical: **{hrow['incident_concept_edges']}** concept relations "
            f"({hrow['outgoing_count']} outgoing).",
            f"Historical selected formal statements: "
            f"**{hrow['structured_record_summary']['selected_statement_count']}**; "
            f"root kinds: `{json.dumps(hrow['structured_record_summary']['root_record_kinds'], sort_keys=True)}`.",
            "",
            "**Canonical neighboring assertions (sampling, not a definition):**",
        ])
        for item in (drow["outgoing"] + drow["incoming"]):
            out.append(
                f"- {item['subject_label']} `{item['predicate']}` "
                f"{item['object_label']} (ID `{item['assertion_id']}`)"
            )
        out += [
            "",
            "**Historical concept relations (bounded sample, not reviewed):**",
        ]
        for item in (hrow["outgoing"] + hrow["incoming"])[:12]:
            out.append(
                f"- {item['subject_label']} `{item['predicate']}` "
                f"{item['object_label']}"
            )
        out += ["", "**Open issue:** same slug is not an approved identity crosswalk; "
                     "scope and predicate meaning need review before logical inference.", ""]
    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT)
    parser.add_argument("--historical-native", type=Path, required=True)
    parser.add_argument("--concept", action="append", required=True, dest="concept_slugs")
    parser.add_argument("--examples", type=int, default=12)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    result = build_comparison(
        args.data_root, args.historical_native, args.concept_slugs,
        example_limit=args.examples,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.format == "json" else render_markdown(result))


if __name__ == "__main__":
    main()
