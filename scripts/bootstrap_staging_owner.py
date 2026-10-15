"""Explicit staging-only singleton owner bootstrap. No production support.

Example:
  STAGING_DATABASE_URL=postgresql://... APP_ENV=staging \
    python -m scripts.bootstrap_staging_owner --email person@example.org \
      --confirm BOOTSTRAP-STAGING-OWNER

The SQL migration must already exist. No tokens or privileged sessions are issued.
"""
from __future__ import annotations

import argparse
import os
from uuid import uuid4

import psycopg


def bootstrap_owner(cursor, email: str) -> str:
    normalized = email.strip().lower()
    if normalized != email or len(email) < 3 or "@" not in email:
        raise ValueError("email must be supplied as a lowercase normalized address")

    # Concurrent bootstraps serialize. SQL unique active-owner index independently
    # enforces the invariant even if another writer ignores this advisory lock.
    cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", ("curricula-owner-bootstrap-v1",))
    cursor.execute("select id, email, active from admin.owner_principal for update")
    rows = cursor.fetchall()
    if rows:
        if len(rows) == 1 and rows[0][1] == normalized and rows[0][2]:
            return str(rows[0][0])
        raise ValueError("owner is already provisioned or disabled; manual audited recovery required")

    identifier = uuid4()
    cursor.execute(
        "insert into admin.owner_principal (id, email, role, active) "
        "values (%s, %s, 'owner', true)",
        (identifier, normalized),
    )
    cursor.execute(
        "insert into admin.owner_audit (owner_id, event_type) "
        "values (%s, 'owner_bootstrapped')",
        (identifier,),
    )
    return str(identifier)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    if os.getenv("APP_ENV", "").lower() != "staging":
        parser.error("APP_ENV=staging is required; production bootstrap is prohibited")
    if args.confirm != "BOOTSTRAP-STAGING-OWNER":
        parser.error("explicit staging bootstrap confirmation is required")
    url = os.getenv("STAGING_DATABASE_URL")
    if not url:
        parser.error("STAGING_DATABASE_URL is required; no production DB fallback")

    with psycopg.connect(url, application_name="curricula-staging-owner-bootstrap") as db:
        with db.cursor() as cursor:
            identifier = bootstrap_owner(cursor, args.email)
    print(f"staging owner principal ensured: {identifier} (no session issued)")


if __name__ == "__main__":
    main()
