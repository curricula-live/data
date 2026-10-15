"""Actual PostgreSQL integration tests of the data-owned owner DDL.

Runs only against the isolated disposable PostgreSQL service in CI.
Never connects to a production runtime or requests user credentials.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from scripts.bootstrap_staging_owner import bootstrap_owner

DSN = os.getenv("TEST_POSTGRES_DSN")
ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not DSN, reason="requires isolated TEST_POSTGRES_DSN")


@pytest.fixture(scope="module", autouse=True)
def install_staging_schema():
    with psycopg.connect(DSN, autocommit=True) as conn:
        migration = (ROOT / "database/migrations/0002_admin_owner.sql").read_text()
        conn.execute(migration)
        # Rerunning an already-installed migration must be harmless.
        conn.execute(migration)


@pytest.fixture
def db():
    connection = psycopg.connect(DSN)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def owner(db, email="owner@example.org"):
    owner_id = uuid4()
    db.execute(
        "insert into admin.owner_principal (id, email) values (%s, %s)",
        (owner_id, email),
    )
    return owner_id


def test_at_most_one_active_owner_and_distinct_email(db):
    owner(db)
    with pytest.raises(UniqueViolation):
        with db.transaction():
            owner(db, "other@example.org")
    assert db.execute("select count(*) from admin.owner_principal where active").fetchone()[0] == 1


def test_invalid_role_or_email_rejected_by_postgres(db):
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_principal (id,email,role) values (%s,%s,%s)",
                (uuid4(), "owner@example.org", "super_admin"),
            )
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_principal (id,email) values (%s,%s)",
                (uuid4(), "Owner@Example.org"),
            )


def test_staging_bootstrap_is_idempotent_and_refuses_transfer(db):
    with db.cursor() as cursor:
        first = bootstrap_owner(cursor, "owner@example.org")
        assert bootstrap_owner(cursor, "owner@example.org") == first
        with pytest.raises(ValueError, match="already provisioned"):
            bootstrap_owner(cursor, "other@example.org")
    assert db.execute(
        "select count(*) from admin.owner_audit where event_type='owner_bootstrapped'"
    ).fetchone()[0] == 1


def test_digest_only_and_known_owner_foreign_keys(db):
    principal = owner(db)
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=15)
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.email_challenge "
                "(id,owner_id,token_hash,issued_at,expires_at) values (%s,%s,%s,%s,%s)",
                (uuid4(), principal, "plaintext-token", now, expiry),
            )
    with pytest.raises(ForeignKeyViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_session "
                "(id,owner_id,token_hash,issued_at,expires_at) values (%s,%s,%s,%s,%s)",
                (uuid4(), uuid4(), "a" * 64, now, expiry),
            )


def test_atomic_one_use_challenge_consumption(db):
    principal = owner(db)
    now = datetime.now(timezone.utc)
    token_hash = "b" * 64
    challenge_id = uuid4()
    db.execute(
        "insert into admin.email_challenge "
        "(id,owner_id,token_hash,issued_at,expires_at) values (%s,%s,%s,%s,%s)",
        (challenge_id, principal, token_hash, now - timedelta(minutes=1), now + timedelta(minutes=5)),
    )
    sql = (
        "update admin.email_challenge set consumed_at = now() "
        "where token_hash=%s and consumed_at is null and issued_at<=now() and expires_at>now() "
        "returning owner_id"
    )
    assert db.execute(sql, (token_hash,)).fetchone()[0] == principal
    assert db.execute(sql, (token_hash,)).fetchone() is None


def test_session_revocation_and_inactive_owner_checks(db):
    principal = owner(db)
    session = uuid4()
    now = datetime.now(timezone.utc)
    db.execute(
        "insert into admin.owner_session "
        "(id,owner_id,token_hash,issued_at,expires_at) values (%s,%s,%s,%s,%s)",
        (session, principal, "c" * 64, now - timedelta(minutes=1), now + timedelta(hours=1)),
    )
    check_sql = (
        "select s.id from admin.owner_session s "
        "join admin.owner_principal p on s.owner_id=p.id "
        "where s.token_hash=%s and s.revoked_at is null and s.expires_at>now() "
        "and p.active and p.role='owner'"
    )
    assert db.execute(check_sql, ("c" * 64,)).fetchone()[0] == session
    db.execute("update admin.owner_session set revoked_at=now() where id=%s", (session,))
    assert db.execute(check_sql, ("c" * 64,)).fetchone() is None


def test_audit_cannot_store_arbitrary_event(db):
    principal = owner(db)
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_audit (owner_id,event_type) values (%s,%s)",
                (principal, "raw_password_or_token"),
            )
