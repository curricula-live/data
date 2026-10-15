"""Read-only staging comparison of the legacy PostgreSQL graph against v2 Git.

Run:
    python -m scripts.verify_staging_parity --database-url "$STAGING_DATABASE_URL"
    python -m scripts.verify_staging_parity --database-url "$STAGING_DATABASE_URL" --require-v2

Uses a read-only repeatable-read transaction. It *never* publishes data,
applies schema DDL, promotes a branch or treats a source claim as reviewed.

The legacy public graph is compared to the preserved one-time UUID ledger and
the imported statement cohort. Current slugs may legitimately differ from
historical slugs; canonical concept/statement UUIDs cannot.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

import psycopg
from psycopg import IsolationLevel

from scripts import publish
from scripts.verify_legacy_identities import read_jsonl, verify_imported_statements
from scripts.staging_parity_evidence import (
    build_evidence, check_read_only_target, verified_git_head, write_evidence_exclusive,
)

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LegacySnapshot:
    concept_slugs: tuple[str, ...]
    predicate_slugs: tuple[str, ...]
    relations: tuple[tuple[str, str, str, str], ...]


def fetch_legacy_snapshot(cursor: Any) -> LegacySnapshot:
    """Fetch existing v1 tables in a single consistent read-only transaction."""
    cursor.execute("select slug from public.concept order by slug")
    concepts = tuple(row[0] for row in cursor.fetchall())
    cursor.execute("select slug from public.relation_type order by slug")
    predicates = tuple(row[0] for row in cursor.fetchall())
    cursor.execute(
        "select id::text, source, type, target from public.relation order by id::text"
    )
    relations = tuple(
        (str(row[0]), str(row[1]), str(row[2]), str(row[3]))
        for row in cursor.fetchall()
    )
    return LegacySnapshot(concepts, predicates, relations)


def _unique(values: Iterable[str], label: str) -> set[str]:
    materialized = list(values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"duplicate {label}")
    return set(materialized)


def compare_legacy_to_canonical(
    snapshot: LegacySnapshot,
    *,
    manifest: dict[str, Any],
    identity_ledger: list[dict[str, str]],
    concepts: list[dict[str, Any]],
    predicates: list[dict[str, Any]],
    statements: list[dict[str, Any]],
    statement_ledger: list[str],
) -> dict[str, int]:
    """Fail if any migrated graph identity or original triple was lost/changed.

    The comparison is migration-focused, *not* academic review. Extra post-v2
    concepts/statements are permitted; the imported cohort must still match.
    """
    counts = manifest["counts"]
    for key, actual in (
        ("concepts", len(snapshot.concept_slugs)),
        ("predicates", len(snapshot.predicate_slugs)),
        ("statements", len(snapshot.relations)),
    ):
        if actual != counts[key]:
            raise ValueError(f"legacy {key} count mismatch: {actual} != {counts[key]}")

    v1_concepts = _unique(snapshot.concept_slugs, "legacy concept slugs")
    v1_predicates = _unique(snapshot.predicate_slugs, "legacy predicate slugs")
    ledger_slugs = _unique((row["legacy_slug"] for row in identity_ledger), "identity ledger slugs")
    if v1_concepts != ledger_slugs:
        raise ValueError("legacy PostgreSQL concept slugs do not match identity ledger")

    mapped_by_slug = {row["legacy_slug"]: str(UUID(row["id"])) for row in identity_ledger}
    canonical_ids = _unique((row["id"] for row in concepts), "canonical concept UUIDs")
    if not set(mapped_by_slug.values()) <= canonical_ids:
        raise ValueError("canonical knowledge corpus lost migrated concept UUIDs")

    known_predicates = _unique((row["slug"] for row in predicates), "canonical predicates")
    if not v1_predicates <= known_predicates:
        raise ValueError("legacy PostgreSQL predicates missing in Git corpus")

    legacy_relations_by_id: dict[str, tuple[str, str, str]] = {}
    for statement_id, source_slug, predicate, target_slug in snapshot.relations:
        identifier = str(UUID(statement_id))
        if identifier in legacy_relations_by_id:
            raise ValueError(f"duplicate legacy relation UUID: {identifier}")
        if source_slug not in mapped_by_slug or target_slug not in mapped_by_slug:
            raise ValueError(f"legacy relation {identifier} refers to unknown legacy concept")
        if predicate not in v1_predicates:
            raise ValueError(f"legacy relation {identifier} has unknown predicate")
        legacy_relations_by_id[identifier] = (source_slug, predicate, target_slug)

    if set(legacy_relations_by_id) != _unique(statement_ledger, "statement UUID ledger"):
        raise ValueError("legacy PostgreSQL relation UUIDs differ from committed statement ledger")

    canonical_by_id = {row["id"]: row for row in statements}
    if len(canonical_by_id) != len(statements):
        raise ValueError("duplicate canonical statement UUID")

    for statement_id, (source_slug, predicate, target_slug) in legacy_relations_by_id.items():
        record = canonical_by_id.get(statement_id)
        if record is None:
            raise ValueError(f"missing migrated statement UUID {statement_id}")
        expected = (
            {"kind": "concept", "id": mapped_by_slug[source_slug]},
            predicate,
            {"kind": "concept", "id": mapped_by_slug[target_slug]},
        )
        actual = (record["subject"], record["predicate"], record["object"])
        if actual != expected:
            raise ValueError(f"migrated statement content changed: {statement_id}")

    return {
        "legacy_concepts": len(v1_concepts),
        "legacy_predicates": len(v1_predicates),
        "legacy_statements": len(legacy_relations_by_id),
        "canonical_concepts": len(concepts),
        "canonical_statements": len(statements),
    }


def load_git_state(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / "migration/legacy-v1/manifest.json").read_text(encoding="utf-8"))
    return {
        "manifest": manifest,
        "identity_ledger": read_jsonl(root / "migration/legacy-v1/concept-identities.jsonl"),
        "concepts": read_jsonl(root / "knowledge/concepts.jsonl"),
        "predicates": read_jsonl(root / "knowledge/predicates.jsonl"),
        "statements": read_jsonl(root / "knowledge/statements.jsonl"),
        "statement_ledger": [
            line for line in (root / "migration/legacy-v1/statement-uuids.txt").read_text(
                encoding="utf-8"
            ).splitlines() if line.strip()
        ],
    }


def verify_staging(
    connection: Any, root: Path = ROOT, *, require_v2: bool = False,
    expected_database: str | None = None, expected_role: str | None = None,
) -> dict[str, Any]:
    git_state = load_git_state(root)
    if verify_imported_statements(root) != git_state["manifest"]["counts"]["statements"]:
        raise ValueError("Git statement identity verification failed")

    # Caller must set transaction isolation before its first SQL statement.
    with connection.cursor() as cursor:
        if expected_database is not None and expected_role is not None:
            check_read_only_target(cursor, expected_database, expected_role)
        legacy = fetch_legacy_snapshot(cursor)
        result = compare_legacy_to_canonical(legacy, **git_state)

        cursor.execute("select to_regclass('knowledge.concept')")
        v2_available = cursor.fetchone()[0] is not None
        if require_v2 and not v2_available:
            raise ValueError("v2 knowledge schema is absent from staging")
        if v2_available:
            publish.require_target_schema(cursor)
            v2_state = publish.fetch_database_state(cursor)
            plan = publish.build_plan(
                {
                    key: git_state[key]
                    for key in ("concepts", "predicates", "statements")
                } | {"definitions": read_jsonl(root / "knowledge/definitions.jsonl")},
                v2_state,
            )
            if publish.has_changes(plan):
                raise ValueError("v2 PostgreSQL differs from canonical Git corpus")
            result["v2_runtime_parity"] = "verified"
        else:
            result["v2_runtime_parity"] = "schema-not-installed"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("STAGING_DATABASE_URL"))
    parser.add_argument("--require-v2", action="store_true")
    parser.add_argument("--expected-database", help="Exact independently verified staging DB name")
    parser.add_argument("--expected-role", help="Exact SELECT-only staging PostgreSQL role")
    parser.add_argument("--expected-git-sha", help="Full reviewed 40-character Git release SHA")
    parser.add_argument("--evidence-out", type=Path, help="Exclusive private JSON evidence file")
    args = parser.parse_args()
    if bool(args.expected_database) != bool(args.expected_role):
        parser.error("--expected-database and --expected-role must be supplied together")
    if args.evidence_out and (
        not args.require_v2 or not args.expected_database
        or not args.expected_role or not args.expected_git_sha
    ):
        parser.error("evidence requires --require-v2 and all three expected target/Git values")
    if not args.database_url:
        parser.error("STAGING_DATABASE_URL or --database-url required (staging only)")

    # Verify the exact checked-out corpus before contacting the staging DB.
    git_commit = verified_git_head(ROOT, args.expected_git_sha) if args.evidence_out else None

    with psycopg.connect(
        args.database_url,
        application_name="curricula-live-staging-parity-read-only",
    ) as connection:
        connection.read_only = True
        connection.isolation_level = IsolationLevel.REPEATABLE_READ
        result = verify_staging(
            connection, require_v2=args.require_v2,
            expected_database=args.expected_database, expected_role=args.expected_role,
        )
    if args.evidence_out:
        evidence = build_evidence(
            root=ROOT, git_commit=git_commit,
            target={"database": args.expected_database, "role": args.expected_role},
            result=result,
        )
        write_evidence_exclusive(args.evidence_out, evidence)
    print(json.dumps({"result": "verified", **result}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
