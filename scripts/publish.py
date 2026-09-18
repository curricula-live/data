from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path
from typing import Any, Callable

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
REQUIRED_TABLES = (
    "knowledge.concept",
    "knowledge.predicate",
    "knowledge.statement",
    "knowledge.definition",
    "knowledge.definition_statement",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path.relative_to(ROOT)}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path.relative_to(ROOT)}:{number}: expected JSON object")
        rows.append(row)
    return rows


def load_canonical_state() -> dict[str, list[dict[str, Any]]]:
    return {
        "concepts": read_jsonl(KNOWLEDGE / "concepts.jsonl"),
        "predicates": read_jsonl(KNOWLEDGE / "predicates.jsonl"),
        "statements": read_jsonl(KNOWLEDGE / "statements.jsonl"),
        "definitions": read_jsonl(KNOWLEDGE / "definitions.jsonl"),
    }


def connect(database_url: str | None = None) -> psycopg.Connection:
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    return psycopg.connect(url, application_name="curricula-live-data-publish")


def require_target_schema(cursor: psycopg.Cursor) -> None:
    missing: list[str] = []
    for table in REQUIRED_TABLES:
        cursor.execute("select to_regclass(%s)", (table,))
        if cursor.fetchone()[0] is None:
            missing.append(table)
    if missing:
        raise SystemExit(
            "target knowledge schema is not installed: "
            + ", ".join(missing)
            + ". Apply reviewed provider-neutral database migrations separately before publishing."
        )


def _statement_from_database(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        statement_id,
        subject_concept_id,
        subject_statement_id,
        predicate_slug,
        object_concept_id,
        object_statement_id,
        literal_value,
        literal_datatype,
    ) = row

    subject = (
        {"kind": "concept", "id": subject_concept_id}
        if subject_concept_id is not None
        else {"kind": "statement", "id": subject_statement_id}
    )
    if object_concept_id is not None:
        object_value: dict[str, Any] = {"kind": "concept", "id": object_concept_id}
    elif object_statement_id is not None:
        object_value = {"kind": "statement", "id": object_statement_id}
    else:
        object_value = {
            "kind": "literal",
            "datatype": literal_datatype,
            "value": literal_value,
        }

    return {
        "id": statement_id,
        "subject": subject,
        "predicate": predicate_slug,
        "object": object_value,
    }


def fetch_database_state(cursor: psycopg.Cursor) -> dict[str, list[dict[str, Any]]]:
    cursor.execute("select id::text, slug, label from knowledge.concept order by id::text")
    concepts = [
        {"id": row[0], "slug": row[1], "label": row[2]}
        for row in cursor.fetchall()
    ]

    cursor.execute("select slug, label from knowledge.predicate order by slug")
    predicates = [
        {"slug": row[0], "label": row[1]}
        for row in cursor.fetchall()
    ]

    cursor.execute(
        """
        select
            id::text,
            subject_concept_id::text,
            subject_statement_id::text,
            predicate_slug,
            object_concept_id::text,
            object_statement_id::text,
            literal_value,
            literal_datatype
        from knowledge.statement
        order by id::text
        """
    )
    statements = [_statement_from_database(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        select
            definition.concept_id::text,
            coalesce(
                array_agg(definition_statement.statement_id::text order by definition_statement.position)
                    filter (where definition_statement.statement_id is not null),
                array[]::text[]
            )
        from knowledge.definition definition
        left join knowledge.definition_statement definition_statement
            on definition_statement.concept_id = definition.concept_id
        group by definition.concept_id
        order by definition.concept_id::text
        """
    )
    definitions = [
        {"concept_id": row[0], "statement_ids": list(row[1])}
        for row in cursor.fetchall()
    ]

    return {
        "concepts": concepts,
        "predicates": predicates,
        "statements": statements,
        "definitions": definitions,
    }


def _diff(
    repository_rows: list[dict[str, Any]],
    database_rows: list[dict[str, Any]],
    key: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    repository = {key(row): row for row in repository_rows}
    database = {key(row): row for row in database_rows}

    add = sorted(repository.keys() - database.keys())
    remove = sorted(database.keys() - repository.keys())
    update = sorted(
        identity
        for identity in repository.keys() & database.keys()
        if repository[identity] != database[identity]
    )

    return {
        "add": len(add),
        "update": len(update),
        "remove": len(remove),
        "samples": {
            "add": add[:10],
            "update": update[:10],
            "remove": remove[:10],
        },
    }


def build_plan(
    repository: dict[str, list[dict[str, Any]]],
    database: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "concepts": _diff(repository["concepts"], database["concepts"], lambda row: row["id"]),
        "predicates": _diff(repository["predicates"], database["predicates"], lambda row: row["slug"]),
        "statements": _diff(repository["statements"], database["statements"], lambda row: row["id"]),
        "definitions": _diff(repository["definitions"], database["definitions"], lambda row: row["concept_id"]),
    }


def has_changes(plan: dict[str, Any]) -> bool:
    return any(
        section[action]
        for section in plan.values()
        for action in ("add", "update", "remove")
    )


def print_plan(plan: dict[str, Any]) -> None:
    print(json.dumps(plan, indent=2, ensure_ascii=False))


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _statement_parameters(statement: dict[str, Any]) -> tuple[Any, ...]:
    subject = statement["subject"]
    object_value = statement["object"]

    subject_concept_id = _uuid(subject["id"]) if subject["kind"] == "concept" else None
    subject_statement_id = _uuid(subject["id"]) if subject["kind"] == "statement" else None

    object_concept_id = _uuid(object_value["id"]) if object_value["kind"] == "concept" else None
    object_statement_id = _uuid(object_value["id"]) if object_value["kind"] == "statement" else None
    literal_value = Jsonb(object_value["value"]) if object_value["kind"] == "literal" else None
    literal_datatype = object_value["datatype"] if object_value["kind"] == "literal" else None

    return (
        _uuid(statement["id"]),
        subject_concept_id,
        subject_statement_id,
        statement["predicate"],
        object_concept_id,
        object_statement_id,
        literal_value,
        literal_datatype,
    )


def _delete_not_in(
    cursor: psycopg.Cursor,
    table: str,
    column: str,
    values: list[Any],
    cast: str,
) -> None:
    if values:
        cursor.execute(
            f"delete from {table} where not ({column} = any(%s::{cast}[]))",
            (values,),
        )
    else:
        cursor.execute(f"delete from {table}")


def apply_canonical_state(
    cursor: psycopg.Cursor,
    canonical: dict[str, list[dict[str, Any]]],
) -> None:
    cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", ("curricula-live-data-publish",))
    cursor.execute("set constraints all deferred")

    current = fetch_database_state(cursor)
    target_concepts = {row["id"]: row for row in canonical["concepts"]}

    # Free slugs held by renamed or soon-to-be-removed rows before canonical upserts.
    for row in current["concepts"]:
        target = target_concepts.get(row["id"])
        if target is None or target["slug"] != row["slug"]:
            cursor.execute(
                "update knowledge.concept set slug = %s where id = %s",
                (f"tmp-{row['id']}", _uuid(row["id"])),
            )

    cursor.executemany(
        """
        insert into knowledge.concept (id, slug, label)
        values (%s, %s, %s)
        on conflict (id) do update set
            slug = excluded.slug,
            label = excluded.label
        where (knowledge.concept.slug, knowledge.concept.label)
            is distinct from
              (excluded.slug, excluded.label)
        """,
        [(_uuid(row["id"]), row["slug"], row["label"]) for row in canonical["concepts"]],
    )

    cursor.executemany(
        """
        insert into knowledge.predicate (slug, label)
        values (%s, %s)
        on conflict (slug) do update set
            label = excluded.label
        where knowledge.predicate.label is distinct from excluded.label
        """,
        [(row["slug"], row["label"]) for row in canonical["predicates"]],
    )

    cursor.executemany(
        """
        insert into knowledge.statement (
            id,
            subject_concept_id,
            subject_statement_id,
            predicate_slug,
            object_concept_id,
            object_statement_id,
            literal_value,
            literal_datatype
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update set
            subject_concept_id = excluded.subject_concept_id,
            subject_statement_id = excluded.subject_statement_id,
            predicate_slug = excluded.predicate_slug,
            object_concept_id = excluded.object_concept_id,
            object_statement_id = excluded.object_statement_id,
            literal_value = excluded.literal_value,
            literal_datatype = excluded.literal_datatype
        where (
            knowledge.statement.subject_concept_id,
            knowledge.statement.subject_statement_id,
            knowledge.statement.predicate_slug,
            knowledge.statement.object_concept_id,
            knowledge.statement.object_statement_id,
            knowledge.statement.literal_value,
            knowledge.statement.literal_datatype
        ) is distinct from (
            excluded.subject_concept_id,
            excluded.subject_statement_id,
            excluded.predicate_slug,
            excluded.object_concept_id,
            excluded.object_statement_id,
            excluded.literal_value,
            excluded.literal_datatype
        )
        """,
        [_statement_parameters(row) for row in canonical["statements"]],
    )

    # Definition membership is small and ordered; rebuild it atomically.
    cursor.execute("delete from knowledge.definition_statement")
    definition_ids = [_uuid(row["concept_id"]) for row in canonical["definitions"]]
    _delete_not_in(cursor, "knowledge.definition", "concept_id", definition_ids, "uuid")

    cursor.executemany(
        "insert into knowledge.definition (concept_id) values (%s) on conflict do nothing",
        [(_uuid(row["concept_id"]),) for row in canonical["definitions"]],
    )
    definition_members: list[tuple[uuid.UUID, uuid.UUID, int]] = []
    for definition in canonical["definitions"]:
        for position, statement_id in enumerate(definition["statement_ids"], start=1):
            definition_members.append(
                (_uuid(definition["concept_id"]), _uuid(statement_id), position)
            )
    if definition_members:
        cursor.executemany(
            """
            insert into knowledge.definition_statement (concept_id, statement_id, position)
            values (%s, %s, %s)
            """,
            definition_members,
        )

    _delete_not_in(
        cursor,
        "knowledge.statement",
        "id",
        [_uuid(row["id"]) for row in canonical["statements"]],
        "uuid",
    )
    _delete_not_in(
        cursor,
        "knowledge.predicate",
        "slug",
        [row["slug"] for row in canonical["predicates"]],
        "text",
    )
    _delete_not_in(
        cursor,
        "knowledge.concept",
        "id",
        [_uuid(row["id"]) for row in canonical["concepts"]],
        "uuid",
    )


def command_plan(database_url: str | None) -> None:
    canonical = load_canonical_state()
    with connect(database_url) as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            require_target_schema(cursor)
            database = fetch_database_state(cursor)
    print_plan(build_plan(canonical, database))


def command_verify(database_url: str | None) -> None:
    canonical = load_canonical_state()
    with connect(database_url) as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            require_target_schema(cursor)
            database = fetch_database_state(cursor)
    plan = build_plan(canonical, database)
    print_plan(plan)
    if has_changes(plan):
        raise SystemExit("database drift detected: runtime does not match canonical Git state")
    print("verified: PostgreSQL runtime matches canonical Git state")


def command_apply(database_url: str | None, confirmation: str) -> None:
    if confirmation != "PUBLISH":
        raise SystemExit("apply requires --confirm-publish PUBLISH")

    canonical = load_canonical_state()
    with connect(database_url) as connection:
        with connection.cursor() as cursor:
            require_target_schema(cursor)
            before = build_plan(canonical, fetch_database_state(cursor))
            print("publish plan:")
            print_plan(before)
            apply_canonical_state(cursor, canonical)
            after = build_plan(canonical, fetch_database_state(cursor))
            if has_changes(after):
                raise RuntimeError(
                    "post-publish verification failed; transaction will be rolled back:\n"
                    + json.dumps(after, indent=2)
                )

    print("published canonical Git state and verified exact runtime match")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish canonical curricula.live Git knowledge to provider-neutral PostgreSQL."
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    commands.add_parser("verify")
    apply_parser = commands.add_parser("apply")
    apply_parser.add_argument("--confirm-publish", default="")
    args = parser.parse_args()

    if args.command == "plan":
        command_plan(args.database_url)
    elif args.command == "verify":
        command_verify(args.database_url)
    else:
        command_apply(args.database_url, args.confirm_publish)


if __name__ == "__main__":
    main()
