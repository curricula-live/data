"""Recover archived V1 concept identifiers and scientific-graph links as review-only records.

Never interpret historical broaderTopic as subtype_of, equivalence, or prerequisite.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "sources" / "historical-v1"
EXPECTED = "4e6ff79570b68de6a6d1d1d4136dcb413e26b999af05fa0ea19cb329ab50df58"
PREFIX = "https://curricula.live/knowledge/computing/concept/"

def dump(rows):
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)

def build(source: Path, dest: Path = DEST, expected=EXPECTED):
    contents = source.read_bytes()
    sha = hashlib.sha256(contents).hexdigest()
    if sha != expected:
        raise ValueError("Historical source fingerprint mismatch: " + sha)
    data = json.loads(contents)
    concepts = {e["id"]: e for e in data["entities"] if e["id"].startswith(PREFIX)}
    if not concepts:
        raise ValueError("No scientific concept records")
    terms = [
        {"source_uri": uri, "label": e["labels"]["en"], "kind": e["kind"],
         "module": e["module"], "identity_status": e.get("identityStatus", "unknown")}
        for uri, e in sorted(concepts.items())
    ]
    relations = []
    counts = Counter()
    for r in data["assertions"]:
        obj = r["object"]
        objid = obj.get("id") if isinstance(obj, dict) else obj
        if r["subject"] not in concepts or objid not in concepts:
            continue
        counts[r["predicate"]] += 1
        relations.append({"assertion_id": r["id"], "subject_uri": r["subject"],
                          "predicate": r["predicate"], "object_uri": objid,
                          "assertion_status": r.get("assertionStatus", "unknown"),
                          "independently_reviewed": False})
    relations.sort(key=lambda x: x["assertion_id"])
    canonical = defaultdict(list)
    for line in (ROOT / "knowledge/concepts.jsonl").read_text().splitlines():
        if line.strip():
            e = json.loads(line)
            canonical[" ".join(e["label"].casefold().split())].append(e["id"])
    matches = [
        {"source_uri": t["source_uri"], "source_label": t["label"],
         "canonical_candidate_ids": sorted(canonical[" ".join(t["label"].casefold().split())]),
         "match_method": "casefolded_exact_label", "review_status": "proposed_not_approved"}
        for t in terms if " ".join(t["label"].casefold().split()) in canonical
    ]
    manifest = {
        "schema": "curricula.source-catalog@1",
        "source_id": "curricula-ontology-archived-v1", "source_version": "1.0.0",
        "source_repository": "https://github.com/curricula-live/ontology",
        "input_name": "ontology-consolidated.json", "input_sha256": expected,
        "review_status": "archived_unreviewed_not_canonical",
        "independent_scientific_approval": False,
        "cross_source_identity_approved": False,
        "curriculum_prerequisites_inferred": False,
        "topic_count": len(terms), "uri_relation_count": len(relations),
        "predicate_counts": dict(sorted(counts.items())),
        "canonical_lexical_candidate_count": len(matches)
    }
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "terms.jsonl").write_text(dump(terms), encoding="utf-8")
    (dest / "relations.jsonl").write_text(dump(relations), encoding="utf-8")
    (dest / "canonical-identity-candidates.jsonl").write_text(dump(matches), encoding="utf-8")
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", type=Path, default=DEST)
    args = p.parse_args()
    print(json.dumps(build(args.source, args.output), indent=2))
