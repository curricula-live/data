#!/usr/bin/env python
import argparse
import json
import os
from pathlib import Path

import psycopg
from jsonschema import Draft202012Validator
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "data" / "concepts.jsonl"
RELATIONS = ROOT / "data" / "relations.jsonl"
CONCEPT_SCHEMA = ROOT / "schema" / "concept.schema.json"
RELATION_SCHEMA = ROOT / "schema" / "relation.schema.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{number}: {exc}") from exc
    return rows


def sort_key(row):
    return tuple(str(row.get(key, "")) for key in ("slug", "source", "type", "target"))


def serialize_jsonl(rows):
    normalized = sorted(rows, key=sort_key)
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in normalized
    )


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_jsonl(rows), encoding="utf-8")


def validate_rows(rows, schema_path, data_path):
    validator = Draft202012Validator(read_json(schema_path))
    failures = []
    for line_number, row in enumerate(rows, 1):
        for error in validator.iter_errors(row):
            location = ".".join(str(part) for part in error.absolute_path)
            suffix = f" ({location})" if location else ""
            failures.append(f"{data_path}:{line_number}{suffix}: {error.message}")
    if failures:
        raise SystemExit("\n".join(failures))


def check(format_check=False, quiet=False):
    concepts = read_jsonl(CONCEPTS)
    relations = read_jsonl(RELATIONS)
    validate_rows(concepts, CONCEPT_SCHEMA, CONCEPTS)
    validate_rows(relations, RELATION_SCHEMA, RELATIONS)

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

    if format_check:
        expected = {
            CONCEPTS: serialize_jsonl(concepts),
            RELATIONS: serialize_jsonl(relations),
        }
        dirty = [str(path) for path, content in expected.items() if path.read_text(encoding="utf-8") != content]
        if dirty:
            raise SystemExit(
                "Non-deterministic JSONL formatting: "
                + ", ".join(dirty)
                + ". Run: python scripts/sync.py format"
            )

    if not quiet:
        print(f"OK: {len(concepts)} concepts, {len(relations)} relations")
    return concepts, relations


def format_data():
    concepts = read_jsonl(CONCEPTS)
    relations = read_jsonl(RELATIONS)
    write_jsonl(CONCEPTS, concepts)
    write_jsonl(RELATIONS, relations)
    check(format_check=True)


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    return psycopg.connect(url, application_name="curricula-live-data-sync")


def fetch_database_state(cursor):
    cursor.execute("select slug, label, description, metadata from concept order by slug")
    concepts = [
        dict(zip(("slug", "label", "description", "metadata"), row))
        for row in cursor.fetchall()
    ]
    cursor.execute(
        """
        select source.slug, target.slug, relation.type, relation.metadata
        from relation
        join concept source on source.id = relation.source
        join concept target on target.id = relation.target
        order by source.slug, relation.type, target.slug
        """
    )
    relations = [
        dict(zip(("source", "target", "type", "metadata"), row))
        for row in cursor.fetchall()
    ]
    return concepts, relations


def relation_key(row):
    return row["source"], row["target"], row["type"]


def build_plan(repo_concepts, repo_relations, database_concepts, database_relations):
    repo_concept_map = {row["slug"]: row for row in repo_concepts}
    database_concept_map = {row["slug"]: row for row in database_concepts}
    repo_relation_map = {relation_key(row): row for row in repo_relations}
    database_relation_map = {relation_key(row): row for row in database_relations}

    concept_add = sorted(repo_concept_map.keys() - database_concept_map.keys())
    concept_remove = sorted(database_concept_map.keys() - repo_concept_map.keys())
    concept_update = sorted(
        slug
        for slug in repo_concept_map.keys() & database_concept_map.keys()
        if repo_concept_map[slug] != database_concept_map[slug]
    )

    relation_add = sorted(repo_relation_map.keys() - database_relation_map.keys())
    relation_remove = sorted(database_relation_map.keys() - repo_relation_map.keys())
    relation_update = sorted(
        key
        for key in repo_relation_map.keys() & database_relation_map.keys()
        if repo_relation_map[key].get("metadata", {})
        != database_relation_map[key].get("metadata", {})
    )

    return {
        "concepts": {
            "add": len(concept_add),
            "update": len(concept_update),
            "remove_if_pruned": len(concept_remove),
            "samples": {
                "add": concept_add[:10],
                "update": concept_update[:10],
                "remove_if_pruned": concept_remove[:10],
            },
        },
        "relations": {
            "add": len(relation_add),
            "update": len(relation_update),
            "remove_if_pruned": len(relation_remove),
            "samples": {
                "add": relation_add[:10],
                "update": relation_update[:10],
                "remove_if_pruned": relation_remove[:10],
            },
        },
    }


def print_plan(summary):
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def pull():
    with connect() as connection, connection.cursor() as cursor:
        concepts, relations = fetch_database_state(cursor)
    write_jsonl(CONCEPTS, concepts)
    write_jsonl(RELATIONS, relations)
    check(format_check=True)
    print(f"Pulled {len(concepts)} concepts and {len(relations)} relations")


def plan():
    repo_concepts, repo_relations = check(format_check=True, quiet=True)
    with connect() as connection, connection.cursor() as cursor:
        database_concepts, database_relations = fetch_database_state(cursor)
    summary = build_plan(
        repo_concepts,
        repo_relations,
        database_concepts,
        database_relations,
    )
    print_plan(summary)
    return summary


def push(apply=False, prune=False, confirm_prune=""):
    repo_concepts, repo_relations = check(format_check=True, quiet=True)
    if prune and confirm_prune != "DELETE":
        raise SystemExit('--prune requires --confirm-prune DELETE')

    with connect() as connection, connection.cursor() as cursor:
        database_concepts, database_relations = fetch_database_state(cursor)
        summary = build_plan(
            repo_concepts,
            repo_relations,
            database_concepts,
            database_relations,
        )
        print_plan(summary)

        if not apply:
            print("Plan only. Re-run with --apply to write changes.")
            connection.rollback()
            return

        for row in repo_concepts:
            cursor.execute(
                """
                insert into concept (slug, label, description, metadata, created_at, updated_at)
                values (%s, %s, %s, %s, now(), now())
                on conflict (slug) do update set
                    label = excluded.label,
                    description = excluded.description,
                    metadata = excluded.metadata,
                    updated_at = now()
                """,
                (
                    row["slug"],
                    row["label"],
                    row["description"],
                    Jsonb(row["metadata"]),
                ),
            )

        for row in repo_relations:
            cursor.execute(
                """
                insert into relation (source, target, type, metadata, created_at, updated_at)
                select source.id, target.id, %s, %s, now(), now()
                from concept source, concept target
                where source.slug = %s and target.slug = %s
                on conflict (source, target, type) do update set
                    metadata = excluded.metadata,
                    updated_at = now()
                """,
                (
                    row["type"],
                    Jsonb(row["metadata"]),
                    row["source"],
                    row["target"],
                ),
            )

        if prune:
            cursor.execute(
                "create temporary table sync_relation_keys(source text, target text, type text) on commit drop"
            )
            relation_keys = [relation_key(row) for row in repo_relations]
            if relation_keys:
                cursor.executemany(
                    "insert into sync_relation_keys values (%s, %s, %s)",
                    relation_keys,
                )
                cursor.execute(
                    """
                    delete from relation relation_row
                    using concept source, concept target
                    where relation_row.source = source.id
                      and relation_row.target = target.id
                      and not exists (
                        select 1 from sync_relation_keys key
                        where key.source = source.slug
                          and key.target = target.slug
                          and key.type = relation_row.type
                      )
                    """
                )
            else:
                cursor.execute("delete from relation")

            concept_slugs = [row["slug"] for row in repo_concepts]
            if concept_slugs:
                cursor.execute(
                    "delete from concept where not (slug = any(%s::text[]))",
                    (concept_slugs,),
                )
            else:
                cursor.execute("delete from concept")

    print(
        f"Applied {len(repo_concepts)} concepts and {len(repo_relations)} relations"
        + (" with pruning" if prune else "")
    )


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    check_parser = commands.add_parser("check")
    check_parser.add_argument("--format", action="store_true", dest="format_check")
    commands.add_parser("format")
    commands.add_parser("pull")
    commands.add_parser("plan")

    push_parser = commands.add_parser("push")
    push_parser.add_argument("--apply", action="store_true")
    push_parser.add_argument("--prune", action="store_true")
    push_parser.add_argument("--confirm-prune", default="")

    args = parser.parse_args()
    if args.command == "check":
        check(format_check=args.format_check)
    elif args.command == "format":
        format_data()
    elif args.command == "pull":
        pull()
    elif args.command == "plan":
        plan()
    else:
        push(
            apply=args.apply,
            prune=args.prune,
            confirm_prune=args.confirm_prune,
        )


if __name__ == "__main__":
    main()
