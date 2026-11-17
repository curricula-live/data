"""Source-scoped, witness-preserving topic paths; NOT semantic entailment.

Only follows CSO superTopicOf or historical broaderTopic. No crosswalk,
cross-source joins, implicit inverses, subtype or learning-prerequisite rules.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSO = "http://cso.kmi.open.ac.uk/schema/cso#superTopicOf"
HIST = "broaderTopic"
SOURCES = {
    "cso": (ROOT / "sources/cso-3.5/topics.jsonl",
            ROOT / "sources/cso-3.5/uri-relations.jsonl.gz",
            "uri", CSO),
    "historical-v1": (ROOT / "sources/historical-v1/terms.jsonl",
                      ROOT / "sources/historical-v1/relations.jsonl",
                      "source_uri", HIST),
}

def read_rows(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)

def paths(source, term, depth=2, limit=40):
    if source not in SOURCES or not 1 <= depth <= 4 or not 1 <= limit <= 100:
        raise ValueError("invalid source, depth or limit")
    topic_file, edge_file, id_key, predicate = SOURCES[source]
    topics = list(read_rows(topic_file))
    by_label = defaultdict(list)
    for t in topics:
        by_label[t["label"].casefold()].append(t[id_key])
    candidates = by_label.get(term.casefold(), [])
    uris = [term] if term.startswith("http") else candidates
    if len(uris) != 1:
        raise ValueError("term must resolve to exactly one source-specific URI")
    start = uris[0]
    adjacency = defaultdict(list)
    for edge in read_rows(edge_file):
        p = edge.get("predicate_uri", edge.get("predicate"))
        if p != predicate:
            continue
        s = edge["subject_uri"]
        target = edge["object_uri"]
        evidence = edge.get("assertion_id") or hashlib.sha256(
            (s + " " + p + " " + target).encode("utf-8")).hexdigest()
        adjacency[s].append((target, evidence))
    for xs in adjacency.values():
        xs.sort(key=lambda x: (x[0], x[1]))
    queue = deque([(start, tuple(), (start,))])
    findings = []
    found = {start}
    truncated = False
    while queue:
        node, witnesses, seen = queue.popleft()
        if len(witnesses) >= depth:
            continue
        for target, assertion in adjacency.get(node, []):
            if target in seen or target in found:
                continue
            found.add(target)
            path = (*witnesses, {
                "subject_uri": node, "predicate": predicate,
                "object_uri": target, "source_assertion": assertion,
            })
            findings.append({
                "target_uri": target, "hop_count": len(path),
                "premise_witnesses": list(path),
                "status": "source_recorded_path_not_logical_entailment",
            })
            if len(findings) == limit:
                truncated = True
                break
            queue.append((target, path, (*seen, target)))
        if truncated:
            break
    return {"source": source, "predicate": predicate, "origin_uri": start,
            "depth": depth, "truncated": truncated, "paths": findings,
            "semantic_subtype_inferred": False, "prerequisite_inferred": False,
            "cross_source_identity_inferred": False}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=sorted(SOURCES), required=True)
    p.add_argument("--term", required=True)
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--limit", type=int, default=20)
    a = p.parse_args()
    print(json.dumps(paths(a.source, a.term, a.depth, a.limit), indent=2))
