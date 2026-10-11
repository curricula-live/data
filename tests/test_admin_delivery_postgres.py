"""Real PostgreSQL constraints for owner auth delivery queue and rate counters."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

DSN = os.getenv("TEST_POSTGRES_DSN")
ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not DSN, reason="requires disposable CI PostgreSQL")


@pytest.fixture(scope="module", autouse=True)
def install_schema():
    with psycopg.connect(DSN, autocommit=True) as conn:
        for path in ("0002_admin_owner.sql", "0003_owner_mail_outbox.sql"):
            code = (ROOT / "database/migrations" / path).read_text(encoding="utf-8")
            conn.execute(code)
            conn.execute(code)


@pytest.fixture
def db():
    with psycopg.connect(DSN) as conn:
        try:
            yield conn
        finally:
            conn.rollback()


def _challenge(db):
    owner = uuid4()
    challenge = uuid4()
    now = datetime.now(timezone.utc)
    db.execute("insert into admin.owner_principal (id, email) values (%s, 'test@example.org')", (owner,))
    db.execute(
        "insert into admin.email_challenge (id,owner_id,token_hash,issued_at,expires_at) "
        "values (%s,%s,%s,%s,%s)",
        (challenge, owner, "a" * 64, now, now + timedelta(minutes=10)),
    )
    return challenge


def test_outbox_only_stores_known_challenge_and_enforces_uniqueness(db):
    ticket = _challenge(db)
    db.execute(
        "insert into admin.owner_email_outbox (id,challenge_id) values (%s,%s)",
        (uuid4(), ticket),
    )
    with pytest.raises(UniqueViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_email_outbox (id,challenge_id) values (%s,%s)",
                (uuid4(), ticket),
            )
    with pytest.raises(ForeignKeyViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_email_outbox (id,challenge_id) values (%s,%s)",
                (uuid4(), uuid4()),
            )


def test_outbox_disallows_double_terminal_state_and_excessive_attempts(db):
    ticket = _challenge(db)
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_email_outbox "
                "(id,challenge_id,attempts) values (%s,%s,6)",
                (uuid4(), ticket),
            )
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_email_outbox "
                "(id,challenge_id,delivered_at,discarded_at) "
                "values (%s,%s,now(),now())",
                (uuid4(), ticket),
            )


def test_rate_buckets_enforce_hashed_keys_and_atomic_limits(db):
    bad = uuid4().hex
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_auth_rate_bucket (bucket_key) values (%s)",
                (bad,),
            )
    key = "b" * 64
    claim = (
        "insert into admin.owner_auth_rate_bucket (bucket_key,attempts) "
        "values (%s,1) on conflict (bucket_key) do update "
        "set attempts=admin.owner_auth_rate_bucket.attempts + 1 "
        "where admin.owner_auth_rate_bucket.attempts < 2 returning attempts"
    )
    assert db.execute(claim, (key,)).fetchone() == (1,)
    assert db.execute(claim, (key,)).fetchone() == (2,)
    assert db.execute(claim, (key,)).fetchone() is None
    assert db.execute(
        "select attempts from admin.owner_auth_rate_bucket where bucket_key=%s", (key,),
    ).fetchone() == (2,)
