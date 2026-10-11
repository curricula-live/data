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


from scripts.owner_mail_outbox import (
    DeliveryLease, claim_next, settle, discard_unusable, prune_rate_buckets,
)


def _queue(db, *, issued_at=None, expires_at=None, consumed_at=None):
    now = datetime.now(timezone.utc)
    issued_at = issued_at or now - timedelta(minutes=1)
    expires_at = expires_at or now + timedelta(minutes=8)
    owner_id, challenge_id, job_id = uuid4(), uuid4(), uuid4()
    db.execute(
        "insert into admin.owner_principal (id,email) values (%s,'queued@example.org')",
        (owner_id,),
    )
    db.execute(
        "insert into admin.email_challenge "
        "(id,owner_id,token_hash,issued_at,expires_at,consumed_at) "
        "values (%s,%s,%s,%s,%s,%s)",
        (challenge_id,owner_id,"f"*64,issued_at,expires_at,consumed_at),
    )
    db.execute(
        "insert into admin.owner_email_outbox (id,challenge_id,available_at) "
        "values (%s,%s,%s)",
        (job_id,challenge_id,now-timedelta(seconds=1)),
    )
    return owner_id, challenge_id, job_id


def test_claim_fences_second_worker_and_success_is_terminal(db):
    now = datetime.now(timezone.utc)
    _, challenge, job = _queue(db)
    lease = claim_next(db, now=now)
    assert isinstance(lease, DeliveryLease)
    assert lease.job_id == job and lease.challenge_id == challenge
    assert lease.attempt == 1 and lease.expires_at > now
    assert claim_next(db, now=now) is None
    assert settle(db, lease, delivered=True, now=now)
    assert not settle(db, lease, delivered=True, now=now)
    assert claim_next(db, now=now) is None
    assert db.execute(
        "select lease_token,leased_until,delivered_at from admin.owner_email_outbox where id=%s",
        (job,),
    ).fetchone()[0:2] == (None, None)


def test_stale_lease_cannot_ack_after_reclaim(db):
    now = datetime.now(timezone.utc)
    _queue(db)
    stale = claim_next(db, now=now)
    assert stale is not None
    later = now + timedelta(seconds=91)
    fresh = claim_next(db, now=later)
    assert fresh is not None and fresh.fence != stale.fence
    assert fresh.attempt == 2
    assert not settle(db, stale, delivered=True, now=later)
    assert settle(db, fresh, delivered=True, now=later)


def test_failure_reschedules_and_fifth_failure_discards(db):
    now = datetime.now(timezone.utc)
    _, _, job = _queue(db)
    first = claim_next(db, now=now)
    assert first and settle(db, first, delivered=False, now=now)
    assert claim_next(db, now=now+timedelta(seconds=15)) is None
    second = claim_next(db, now=now+timedelta(seconds=31))
    assert second and second.attempt == 2
    # Simulate previously exhausted delivery attempts to exercise cap.
    db.execute(
        "update admin.owner_email_outbox "
        "set attempts=5 where id=%s",
        (job,),
    )
    capped = DeliveryLease(job, second.challenge_id, 5, second.fence, second.expires_at)
    assert settle(db, capped, delivered=False, now=now+timedelta(seconds=31))
    assert db.execute(
        "select discarded_at is not null from admin.owner_email_outbox where id=%s",
        (job,),
    ).fetchone()[0]
    assert claim_next(db, now=now+timedelta(minutes=2)) is None


def test_expired_challenge_is_never_sent_and_is_discarded(db):
    now = datetime.now(timezone.utc)
    _queue(db, issued_at=now-timedelta(minutes=9),
           expires_at=now-timedelta(seconds=1))
    assert claim_next(db, now=now) is None
    assert discard_unusable(db, now=now) == 1
    assert discard_unusable(db, now=now) == 0


def test_disabled_owner_prevents_queue_delivery(db):
    now = datetime.now(timezone.utc)
    owner, _, _ = _queue(db)
    db.execute(
        "update admin.owner_principal set active=false,disabled_at=%s where id=%s",
        (now, owner),
    )
    assert claim_next(db, now=now) is None
    assert discard_unusable(db, now=now) == 1


def test_lease_consistency_rejects_unfenced_jobs(db):
    ticket = _challenge(db)
    with pytest.raises(CheckViolation):
        with db.transaction():
            db.execute(
                "insert into admin.owner_email_outbox "
                "(id,challenge_id,leased_until) values (%s,%s,now())",
                (uuid4(), ticket),
            )


def test_rate_bucket_pruning_is_bounded(db):
    now = datetime.now(timezone.utc)
    db.execute(
        "insert into admin.owner_auth_rate_bucket (bucket_key,first_seen_at) "
        "values (%s,%s),(%s,%s),(%s,%s)",
        ("1"*64,now-timedelta(hours=1),
         "2"*64,now-timedelta(hours=1),"3"*64,now),
    )
    assert prune_rate_buckets(db,before=now-timedelta(minutes=20),batch=1) == 1
    assert prune_rate_buckets(db,before=now-timedelta(minutes=20),batch=5) == 1
    assert prune_rate_buckets(db,before=now-timedelta(minutes=20),batch=5) == 0
    assert db.execute(
        "select count(*) from admin.owner_auth_rate_bucket"
    ).fetchone()[0] == 1
