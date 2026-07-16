#!/usr/bin/env python
import argparse
import json
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "data" / "concepts.jsonl"
RELATIONS = ROOT / "data" / "relations.jsonl"


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{number}: {exc}") from exc
    return rows


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = sorted(rows, key=lambda row: tuple(str(row.get(k, "")) for k in ("slug", "source", "type", "target")))
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in normalized), encoding="utf-8")


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    return psycopg.connect(url)


def check():
    concepts = read_jsonl(CONCEPTS)
    relations = read_jsonl(RELATIONS)
    slugs = [row["slug"] for row in concepts]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Duplicate concept slug")
    known = set(slugs)
    keys = set()
    for row in relations:
        key = (row["source"], row["target"], row["type"])
        if key in keys:
            raise SystemExit(f"Duplicate relation: {key}")
        keys.add(key)
        missing = {row["source"], row["target"]} - known
        if missing:
            raise SystemExit(f"Relation references missing concepts: {sorted(missing)}")
    print(f"OK: {len(concepts)} concepts, {len(relations)} relations")


def pull():
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select slug, label, description, metadata from concept order by slug")
        concepts = [dict(zip(("slug", "label", "description", "metadata"), row)) for row in cur.fetchall()]
        cur.execute("""
            select s.slug, t.slug, r.type, r.metadata
            from relation r join concept s on s.id=r.source_id join concept t on t.id=r.target_id
            order by s.slug, r.type, t.slug
        """)
        relations = [dict(zip(("source", "target", "type", "metadata"), row)) for row in cur.fetchall()]
    write_jsonl(CONCEPTS, concepts)
    write_jsonl(RELATIONS, relations)
    print(f"Pulled {len(concepts)} concepts and {len(relations)} relations")


def push(prune=False):
    check()
    concepts = read_jsonl(CONCEPTS)
    relations = read_jsonl(RELATIONS)
    with connect() as conn, conn.cursor() as cur:
        for row in concepts:
            cur.execute("""
                insert into concept (slug,label,description,metadata,created_at,updated_at)
                values (%s,%s,%s,%s,now(),now())
                on conflict (slug) do update set label=excluded.label, description=excluded.description,
                    metadata=excluded.metadata, updated_at=now()
            """, (row["slug"], row["label"], row.get("description", ""), json.dumps(row.get("metadata", {}))))
        for row in relations:
            cur.execute("""
                insert into relation (source_id,target_id,type,metadata,created_at,updated_at)
                select s.id,t.id,%s,%s,now(),now() from concept s, concept t
                where s.slug=%s and t.slug=%s
                on conflict (source_id,target_id,type) do update set metadata=excluded.metadata, updated_at=now()
            """, (row["type"], json.dumps(row.get("metadata", {})), row["source"], row["target"]))
        if prune:
            relation_keys = [(r["source"], r["target"], r["type"]) for r in relations]
            concept_slugs = [c["slug"] for c in concepts]
            cur.execute("create temporary table sync_relation_keys(source text,target text,type text) on commit drop")
            cur.executemany("insert into sync_relation_keys values (%s,%s,%s)", relation_keys)
            cur.execute("""delete from relation r using concept s, concept t
                where r.source_id=s.id and r.target_id=t.id and not exists
                (select 1 from sync_relation_keys k where k.source=s.slug and k.target=t.slug and k.type=r.type)""")
            cur.execute("delete from concept where not (slug = any(%s))", (concept_slugs,))
    print(f"Pushed {len(concepts)} concepts and {len(relations)} relations" + (" with pruning" if prune else ""))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("pull")
    push_parser = sub.add_parser("push")
    push_parser.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    {"check": check, "pull": pull}.get(args.command, lambda: push(args.prune))()

if __name__ == "__main__":
    main()
