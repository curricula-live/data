from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[1]
CONCEPT_NAMESPACE = uuid.UUID("645d16b7-688a-5ffc-aa3d-8b6626ba1383")
EXPECTED_COUNTS = {"concepts": 554, "predicates": 19, "statements": 663}
ACRONYMS = {
    "ai", "api", "ascii", "bcd", "bios", "cpu", "css", "dns", "fifo", "gpu",
    "gui", "html", "http", "https", "ict", "ide", "ip", "ipv4", "ipv6", "iot",
    "lan", "ml", "os", "ram", "rom", "sql", "tcp", "udp", "ui", "url", "usb",
    "uuid", "wan", "wlan", "xml",
}


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def jsonl(rows: list[dict[str, Any]]) -> str:
    return "" if not rows else "\n".join(compact_json(row) for row in rows) + "\n"


def concept_id(slug: str) -> str:
    return str(uuid.uuid5(CONCEPT_NAMESPACE, slug))


def humanize(slug: str) -> str:
    return " ".join(
        word.upper() if word in ACRONYMS else word[:1].upper() + word[1:]
        for word in slug.replace("_", "-").split("-")
    )


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_legacy(database_url: str) -> tuple[list[str], list[str], list[dict[str, str]]]:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select slug from public.concept order by slug")
            concepts = [row[0] for row in cursor.fetchall()]
            cursor.execute("select slug from public.relation_type order by slug")
            predicates = [row[0] for row in cursor.fetchall()]
            cursor.execute("select id::text, source, type, target from public.relation order by id::text")
            relations = [
                {"id": row[0], "source": row[1], "type": row[2], "target": row[3]}
                for row in cursor.fetchall()
            ]
    return concepts, predicates, relations


def build_outputs(
    concept_slugs: list[str],
    predicate_slugs: list[str],
    relations: list[dict[str, str]],
) -> dict[str, str]:
    counts = {"concepts": len(concept_slugs), "predicates": len(predicate_slugs), "statements": len(relations)}
    if counts != EXPECTED_COUNTS:
        raise SystemExit(f"legacy source counts changed: expected {EXPECTED_COUNTS}, got {counts}")
    if len(set(concept_slugs)) != len(concept_slugs):
        raise SystemExit("legacy concepts contain duplicate slugs")
    if len(set(predicate_slugs)) != len(predicate_slugs):
        raise SystemExit("legacy predicates contain duplicate slugs")

    concept_ids = {slug: concept_id(slug) for slug in concept_slugs}
    predicate_set = set(predicate_slugs)
    relation_ids: set[str] = set()
    statements: list[dict[str, Any]] = []

    for relation in relations:
        relation_id = relation["id"]
        if relation_id in relation_ids:
            raise SystemExit(f"duplicate legacy relation UUID: {relation_id}")
        relation_ids.add(relation_id)
        if relation["source"] not in concept_ids or relation["target"] not in concept_ids:
            raise SystemExit(f"relation {relation_id} references an unknown concept")
        if relation["type"] not in predicate_set:
            raise SystemExit(f"relation {relation_id} references unknown predicate {relation['type']}")
        statements.append({
            "id": relation_id,
            "subject": {"kind": "concept", "id": concept_ids[relation["source"]]},
            "predicate": relation["type"],
            "object": {"kind": "concept", "id": concept_ids[relation["target"]]},
        })

    concepts = [{"id": concept_ids[slug], "slug": slug, "label": humanize(slug)} for slug in concept_slugs]
    predicates = [{"slug": slug, "label": humanize(slug)} for slug in predicate_slugs]
    statements.sort(key=lambda row: row["id"])
    ledger = [{"legacy_slug": slug, "id": concept_ids[slug]} for slug in concept_slugs]

    outputs = {
        "knowledge/concepts.jsonl": jsonl(concepts),
        "knowledge/predicates.jsonl": jsonl(predicates),
        "knowledge/statements.jsonl": jsonl(statements),
        "migration/legacy-v1/concept-identities.jsonl": jsonl(ledger),
    }
    manifest = {
        "version": "legacy-v1-to-v2",
        "source": {"database": "production PostgreSQL runtime", "schema": "public", "tables": ["concept", "relation_type", "relation"]},
        "counts": EXPECTED_COUNTS,
        "concept_namespace_uuid": str(CONCEPT_NAMESPACE),
        "concept_identity_strategy": "UUIDv5(namespace, legacy slug) for the one-time migration; committed UUID is authoritative afterwards",
        "statement_identity_strategy": "preserve legacy public.relation.id UUID",
        "label_strategy": "mechanical display label derived from the legacy slug; labels are editorial identifiers, not factual descriptions",
        "sha256": {path: sha256(content) for path, content in outputs.items()},
    }
    outputs["migration/legacy-v1/manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return outputs


def compare_or_write(outputs: dict[str, str], write: bool) -> None:
    mismatches: list[str] = []
    for relative_path, content in outputs.items():
        path = ROOT / relative_path
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        else:
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != content:
                mismatches.append(relative_path)
    if mismatches:
        raise SystemExit("legacy runtime no longer matches committed migration snapshot: " + ", ".join(mismatches))


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only exporter/checker for the legacy production graph.")
    parser.add_argument("--write", action="store_true", help="rewrite canonical migration outputs")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    concepts, predicates, relations = fetch_legacy(args.database_url)
    outputs = build_outputs(concepts, predicates, relations)
    compare_or_write(outputs, args.write)
    mode = "wrote" if args.write else "verified"
    print(f"{mode} legacy migration: {len(concepts)} concepts, {len(predicates)} predicates, {len(relations)} statements")


if __name__ == "__main__":
    main()
