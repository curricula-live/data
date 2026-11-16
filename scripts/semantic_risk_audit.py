"""Read-only structural semantics audit of the canonical source graph.

No scientific statement is certified here: source assertions, their type
interpretation and all structural warnings require independent review.

Usage:
  python scripts/semantic_risk_audit.py --concept array --format markdown
  python scripts/semantic_risk_audit.py --concept integer --format json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_WITNESS = 6

# These are review questions, not inference rules or new canonical predicates.
PREDICATE_QUESTIONS = {
    "subtype_of": "Class subsumption or membership? Is transitivity justified in this context?",
    "uses": "What is the specific role of this dependency? Does it require a narrower predicate?",
    "part_of": "Physical part, conceptual component, domain element or aggregation?",
    "represents": "Symbolic denotation, storage representation or encoding?",
    "prerequisite_of": "Pedagogical prerequisite for which learners, goals and curriculum?",
    "implemented_by": "Implementation of which interface, specification or abstraction?",
}


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def shortest_subtype_path(
    start: str,
    destination: str,
    outgoing: dict[str, list[dict]],
    *,
    exclude_id: str | None = None,
    max_depth: int = MAX_WITNESS,
) -> list[str] | None:
    queue = deque([(start, ())])
    visited = {start}
    while queue:
        current, premises = queue.popleft()
        if len(premises) >= max_depth:
            continue
        for edge in outgoing.get(current, []):
            if edge["id"] == exclude_id:
                continue
            target = edge["target"]
            if target == destination:
                return [*premises, edge["id"]]
            if target not in visited:
                visited.add(target)
                queue.append((target, (*premises, edge["id"])))
    return None


def directed_cycles(nodes: set[str], outgoing: dict[str, list[dict]]) -> list[list[str]]:
    """Find strongly connected classification groups, without judging their meaning."""
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    positions: dict[str, int] = {}
    low: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        positions[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for edge in outgoing.get(node, []):
            other = edge["target"]
            if other not in positions:
                visit(other)
                low[node] = min(low[node], low[other])
            elif other in on_stack:
                low[node] = min(low[node], positions[other])
        if low[node] == positions[node]:
            component: list[str] = []
            while True:
                other = stack.pop()
                on_stack.remove(other)
                component.append(other)
                if other == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in sorted(nodes):
        if node not in positions:
            visit(node)
    return sorted(components)


def build_audit(root: Path = ROOT, focus: str | None = None) -> dict:
    concepts = read_jsonl(root / "knowledge" / "concepts.jsonl")
    statements = read_jsonl(root / "knowledge" / "statements.jsonl")
    predicates = read_jsonl(root / "knowledge" / "predicates.jsonl")
    source_by_id = {c["id"]: c["slug"] for c in concepts}
    if len(source_by_id) != len(concepts):
        raise ValueError("Duplicate canonical concept UUID")
    slugs = set(source_by_id.values())
    if len(slugs) != len(concepts):
        raise ValueError("Duplicate canonical concept slug")
    if focus is not None and focus not in slugs:
        raise ValueError("Not in canonical concept corpus: " + focus)

    predicate_slugs = {p["slug"] for p in predicates}
    if len(predicate_slugs) != len(predicates):
        raise ValueError("Duplicate predicate")
    evidence: list[dict] = []
    statement_ids: set[str] = set()
    for statement in statements:
        identifier = statement["id"]
        if identifier in statement_ids:
            raise ValueError("Duplicate statement UUID")
        statement_ids.add(identifier)
        predicate = statement["predicate"]
        if predicate not in predicate_slugs:
            raise ValueError("Unknown predicate: " + predicate)
        subject, obj = statement["subject"], statement["object"]
        if subject["kind"] != "concept" or obj["kind"] != "concept":
            continue  # A non-concept referent is outside this graph projection.
        if subject["id"] not in source_by_id or obj["id"] not in source_by_id:
            raise ValueError("Statement references unknown concept identity")
        evidence.append({
            "id": identifier,
            "source": source_by_id[subject["id"]],
            "predicate": predicate,
            "target": source_by_id[obj["id"]],
        })

    evidence.sort(key=lambda e: (e["source"], e["predicate"], e["target"], e["id"]))
    subtype = [e for e in evidence if e["predicate"] == "subtype_of"]
    outgoing: dict[str, list[dict]] = defaultdict(list)
    for edge in subtype:
        outgoing[edge["source"]].append(edge)

    cycles = directed_cycles(slugs, outgoing)
    redundant = []
    for edge in subtype:
        alternate = shortest_subtype_path(
            edge["source"], edge["target"], outgoing, exclude_id=edge["id"]
        )
        if alternate and len(alternate) >= 2:
            redundant.append({
                "id": edge["id"], "source": edge["source"], "target": edge["target"],
                "alternative_premise_ids": alternate,
                "status": "review_redundancy_not_semantic_error",
            })

    subtype_parents = {
        slug: sorted(outgoing[slug], key=lambda e: (e["target"], e["id"]))
        for slug in slugs if len(outgoing[slug]) >= 3
    }
    fanout = [{
        "concept": slug, "direct_parent_count": len(edges),
        "statement_ids": [e["id"] for e in edges],
        "parent_slugs": [e["target"] for e in edges],
        "status": "review_multiple_classifications_not_necessarily_conflict",
    } for slug, edges in sorted(subtype_parents.items())]

    uses = {(e["source"], e["target"]): e for e in evidence if e["predicate"] == "uses"}
    inverse_part_pairs = [{
        "subject": e["target"],
        "object": e["source"],
        "uses_id": uses[(e["target"], e["source"])]["id"],
        "part_of_id": e["id"],
        "status": "review_role_distinction_not_conflict",
        "question": "Does 'uses' plus inverse 'part_of' reflect one precise relation or two different senses?",
    } for e in evidence if e["predicate"] == "part_of"
       and (e["target"], e["source"]) in uses]

    connected = [
        e for e in evidence if focus is not None and
        (e["source"] == focus or e["target"] == focus)
    ]
    focus_proofs = [
        e for e in redundant if focus is not None and
        (e["source"] == focus or e["target"] == focus)
    ]
    return {
        "schema_version": "canonical-semantic-structural-audit@1",
        "authorizes_import": False,
        "authorizes_new_inference_rules": False,
        "authorizes_publication": False,
        "origin": "canonical_data_jsonl_read_only",
        "source_credibility": "not_determined_by_structural_analysis",
        "counts": {
            "concepts": len(concepts),
            "statements": len(statements),
            "concept_to_concept_statements": len(evidence),
            "predicates": len(predicates),
            "subtype_statements": len(subtype),
            "subtype_cycle_groups": len(cycles),
            "redundant_subtype_candidates": len(redundant),
            "multiple_parent_candidates": len(fanout),
            "inverse_uses_part_of_candidates": len(inverse_part_pairs),
        },
        "predicate_questions": [
            {"predicate": pred, "review_question": PREDICATE_QUESTIONS.get(
                pred, "Establish domain, range, context and valid inference rules."
            )}
            for pred in sorted(predicate_slugs)
        ],
        "subtype_cycle_groups": cycles,
        "redundant_subtype_candidates": redundant,
        "multiple_parent_candidates": fanout,
        "inverse_uses_part_of_candidates": inverse_part_pairs,
        "focus": None if focus is None else {
            "slug": focus,
            "direct_assertions": connected,
            "redundant_direct_subtype_candidates": focus_proofs,
            "inverse_uses_part_of_candidates": [
                pair for pair in inverse_part_pairs if pair["subject"] == focus
            ],
            "status": "unreviewed",
        },
    }


def to_markdown(report: dict) -> str:
    c = report["counts"]
    lines = [
        "# Canonical structural semantics audit — review candidates only",
        "",
        "This audit verifies graph structure, NOT scientific source authority. No relation is accepted, removed or published.",
        "",
        f"Corpus: {c['concepts']} concepts, {c['statements']} statements, "
        f"{c['predicates']} predicates ({c['subtype_statements']} subtype assertions).",
        "",
        "| Structural check | Flagged candidates |",
        "| --- | ---: |",
        f"| Subtype cycles / strongly connected groups | {c['subtype_cycle_groups']} |",
        f"| Redundant direct subtype edges | {c['redundant_subtype_candidates']} |",
        f"| Concepts with 3+ direct subtype parents | {c['multiple_parent_candidates']} |",
        f"| Paired uses / inverse part_of relations | {c['inverse_uses_part_of_candidates']} |",
        "",
    ]
    if report["focus"]:
        focus = report["focus"]
        lines += [
            f"## Review: {focus['slug']}",
            "",
            "| UUID | Recorded statement |",
            "| --- | --- |",
        ]
        for e in focus["direct_assertions"]:
            lines.append(
                f"| `{e['id']}` | `{e['source']}` —`{e['predicate']}`→ `{e['target']}` |"
            )
        lines += ["", "### Relation-role ambiguity candidates", ""]
        for pair in focus["inverse_uses_part_of_candidates"]:
            lines.append(
                f"- `uses` (`{pair['uses_id']}`) and inverse `part_of` "
                f"(`{pair['part_of_id']}`) between `{pair['subject']}` and "
                f"`{pair['object']}`. **Not an asserted contradiction.**"
            )
        if not focus["inverse_uses_part_of_candidates"]:
            lines.append("No matching inverse `uses`/`part_of` pairs at this node.")
        lines += ["", "### Redundant subtype candidates", ""]
        for row in focus["redundant_direct_subtype_candidates"]:
            refs = ", ".join("`" + x + "`" for x in row["alternative_premise_ids"])
            lines.append(
                f"- `{row['source']}` subtype_of `{row['target']}` (`{row['id']}`) "
                f"has a recorded alternate path: {refs}."
            )
        if not focus["redundant_direct_subtype_candidates"]:
            lines.append("No redundant direct subtype edges detected at this node.")
    lines += [
        "",
        "## Predicate semantics requiring evidence",
        "",
        "| Predicate | Review question |",
        "| --- | --- |",
    ]
    lines += [
        f"| {r['predicate']} | {r['review_question']} |"
        for r in report["predicate_questions"]
    ]
    lines += [
        "",
        "**Conclusion:** structural candidates require human/context/source review; "
        "absence of a flagged cycle or redundancy does not certify semantic soundness.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept", help="Optional existing canonical slug")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path, help="Optional report destination")
    args = parser.parse_args()
    report = build_audit(focus=args.concept)
    result = json.dumps(report, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else to_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
