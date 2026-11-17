"""Pinned, source-preserving CSO3.5 import; no automatic canonical admission."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "sources" / "cso-3.5"
URL = "https://cso.kmi.open.ac.uk/download/version-3.5/CSO.3.5.nt.zip"
SHA = "47e535468e3c9fb9e9da91bc97a3756d472ce8513bd72b094dcd67c65e78d5cc"
TOPIC = "https://cso.kmi.open.ac.uk/topics/"
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
PATTERN = re.compile(r'^<([^<> ]+)> <([^<> ]+)> (<[^<> ]+>|"(?:\\.|[^"\\])*"(?:@[a-zA-Z-]+|\^\^<[^<>]+>)?) \.$')

def rows(archive, expected=SHA):
    data = archive.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != expected:
        raise ValueError("SHA-256 mismatch: " + sha)
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if len(members) != 1 or members[0].filename != "CSO.3.5.nt" or members[0].is_dir():
            raise ValueError("Expected exactly one CSO.3.5.nt member")
        info = members[0]
        if not 0 < info.file_size <= 60_000_000:
            raise ValueError("Unexpected archive size")
        source = z.read(info)
    if len(source) != info.file_size:
        raise ValueError("Uncompressed size mismatch")
    for number, line in enumerate(source.decode("utf-8").splitlines(), 1):
        m = PATTERN.fullmatch(line)
        if not m:
            raise ValueError("Unsupported NTriples line " + str(number))
        s, p, o = m.groups()
        if not s.startswith(TOPIC):
            raise ValueError("Unexpected subject")
        if o.startswith("<"):
            yield s, p, {"kind": "uri", "value": o[1:-1]}
        else:
            lit = re.fullmatch(r'("(?:\\.|[^"\\])*")(?:@([a-zA-Z-]+)|\^\^<([^<>]+)>)?', o)
            if not lit:
                raise ValueError("Unsupported literal")
            q, lang, typ = lit.groups()
            yield s, p, {"kind": "literal", "value": json.loads(q), "lang": lang, "datatype": typ}

def dump(items):
    return ("".join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for r in items)).encode("utf8")

def build(archive, output=DEST, expected=SHA):
    labels, predicates, subjects, relations = {}, Counter(), set(), []
    for s, p, o in rows(archive, expected):
        subjects.add(s)
        predicates[p] += 1
        if o["kind"] == "uri":
            relations.append({"subject_uri": s, "predicate_uri": p, "object_uri": o["value"]})
        else:
            if p != LABEL or o["lang"] != "en":
                raise ValueError("Unmodelled literal")
            if s in labels and labels[s] != o["value"]:
                raise ValueError("Conflicting labels")
            labels[s] = o["value"]
    if not set(labels).issubset(subjects):
        raise ValueError("Label for unknown subject")
    concepts = [{"uri": s, "label": labels[s]} for s in sorted(labels)]
    relations.sort(key=lambda x: (x["subject_uri"], x["predicate_uri"], x["object_uri"]))
    existing = defaultdict(list)
    for line in (ROOT / "knowledge/concepts.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            existing[" ".join(r["label"].casefold().split())].append(r["id"])
    matches = [{"source_uri": t["uri"], "source_label": t["label"],
                "canonical_candidate_ids": sorted(existing[" ".join(t["label"].casefold().split())]),
                "match_method": "casefolded_exact_label", "review_status": "proposed_not_approved"}
               for t in concepts if " ".join(t["label"].casefold().split()) in existing]
    manifest = {"schema": "curricula.source-catalog@1", "source_id": "cso", "source_version": "3.5",
        "release_date": "2025-07-29", "archive_url": URL, "archive_sha256": expected,
        "license": "CC-BY-4.0", "license_url": "https://cso.kmi.open.ac.uk/faq",
        "attribution": "Computer Science Ontology (CSO), The Open University, v3.5",
        "review_status": "source_preserved_not_canonical", "cross_source_identity_approved": False,
        "curriculum_prerequisites_inferred": False, "triple_count": sum(predicates.values()),
        "topic_count": len(concepts), "unlabeled_subject_count": len(subjects - set(labels)), "uri_relation_count": len(relations),
        "predicate_counts": dict(sorted(predicates.items())),
        "canonical_lexical_candidate_count": len(matches)}
    output.mkdir(parents=True, exist_ok=True)
    (output / "CSO.3.5.nt.zip").write_bytes(archive.read_bytes())
    (output / "topics.jsonl").write_bytes(dump(concepts))
    (output / "canonical-identity-candidates.jsonl").write_bytes(dump(matches))
    with (output / "uri-relations.jsonl.gz").open("wb") as f:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, mtime=0, fileobj=f) as gz:
            gz.write(dump(relations))
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

def search(query, source=DEST, limit=20):
    if not (1 <= len(query) <= 120 and 1 <= limit <= 100):
        raise ValueError("query or limit out of bounds")
    needle = " ".join(query.casefold().split())
    hits = []
    for line in (source / "topics.jsonl").open():
        item = json.loads(line)
        label = " ".join(item["label"].casefold().split())
        if needle in label:
            hits.append((0 if label == needle else 1 if label.startswith(needle) else 2,
                         len(label), label, item))
    hits.sort(key=lambda x: x[:3])
    return {"query": query, "source": "cso@3.5", "review_status": "source_only",
            "total": len(hits), "results": [h[3] for h in hits[:limit]]}

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("import")
    a.add_argument("--archive", required=True, type=Path)
    a.add_argument("--output", type=Path, default=DEST)
    b = sub.add_parser("search")
    b.add_argument("query")
    b.add_argument("--limit", type=int, default=20)
    opts = p.parse_args()
    result = build(opts.archive, opts.output) if opts.action == "import" else search(opts.query, limit=opts.limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    main()
