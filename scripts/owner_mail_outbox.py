"""Fenced, transactional PostgreSQL owner email job queue.

This module handles leases, retries and cleanup ONLY; it cannot reconstruct
credentials, send email, enable authentication or connect to production itself.
Caller passes an already reviewed psycopg connection and an aware timestamp.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

LEASE_SECONDS = 90
MAX_ATTEMPTS = 5
MIN_DELIVERY_VALIDITY = timedelta(seconds=30)


@dataclass(frozen=True, slots=True)
class DeliveryLease:
    job_id: UUID
    challenge_id: UUID
    attempt: int
    fence: UUID
    expires_at: datetime


def aware(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("an aware timestamp is required")
    return now.astimezone(timezone.utc)


def claim_next(connection, *, now: datetime) -> DeliveryLease | None:
    """Atomically lease one eligible job without blocking other workers.

    Returns only opaque database UUIDs; no token, email or provider data.
    PostgreSQL SKIP LOCKED prevents duplicate simultaneous claim of a row.
    """
    now = aware(now)
    fence = uuid4()
    expires_at = now + timedelta(seconds=LEASE_SECONDS)
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                with candidate as (
                    select o.id
                    from admin.owner_email_outbox o
                    join admin.email_challenge c on c.id = o.challenge_id
                    join admin.owner_principal p on p.id = c.owner_id
                    where o.delivered_at is null and o.discarded_at is null
                      and o.attempts < %s and o.available_at <= %s
                      and (o.leased_until is null or o.leased_until <= %s)
                      and c.consumed_at is null and c.expires_at > %s
                      and p.active and p.role = 'owner'
                    order by o.available_at, o.id
                    for update of o skip locked
                    limit 1
                )
                update admin.owner_email_outbox o
                set lease_token = %s, leased_until = %s,
                    attempts = o.attempts + 1
                from candidate
                where o.id = candidate.id
                returning o.id, o.challenge_id, o.attempts
                """,
                (
                    MAX_ATTEMPTS, now, now, now + MIN_DELIVERY_VALIDITY,
                    fence, expires_at,
                ),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return DeliveryLease(row[0], row[1], row[2], fence, expires_at)


def settle(connection, lease: DeliveryLease, *, delivered: bool, now: datetime) -> bool:
    """Fence stale workers; mark sent or apply bounded exponential backoff.

    A network delivery can be duplicated following a worker crash. Downstream
    challenge redemption must remain one-use and idempotent.
    """
    now = aware(now)
    if not isinstance(lease, DeliveryLease):
        raise TypeError("expected a delivery lease")
    terminal = not delivered and lease.attempt >= MAX_ATTEMPTS
    delay = timedelta(seconds=min(30 * (2 ** (lease.attempt - 1)), 240))
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update admin.owner_email_outbox
                set delivered_at = case when %s then %s else delivered_at end,
                    discarded_at = case when %s then %s else discarded_at end,
                    available_at = case when %s or %s
                        then available_at else %s end,
                    leased_until = null,
                    lease_token = null
                where id = %s and lease_token = %s
                  and leased_until > %s and attempts = %s
                  and delivered_at is null and discarded_at is null
                returning id
                """,
                (
                    delivered, now, terminal, now,
                    delivered, terminal, now + delay,
                    lease.job_id, lease.fence, now, lease.attempt,
                ),
            )
            return cursor.fetchone() is not None


def discard_unusable(connection, *, now: datetime, batch: int = 100) -> int:
    """Discard expired, consumed, or owner-disabled queued messages."""
    now = aware(now)
    if not 1 <= batch <= 1000:
        raise ValueError("batch size must be between 1 and 1000")
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                with doomed as (
                    select o.id
                    from admin.owner_email_outbox o
                    join admin.email_challenge c on c.id = o.challenge_id
                    join admin.owner_principal p on p.id = c.owner_id
                    where o.delivered_at is null and o.discarded_at is null
                      and (c.expires_at <= %s or c.consumed_at is not null
                           or not p.active
                           or (o.attempts >= 5
                               and (o.leased_until is null or o.leased_until <= %s)))
                    order by o.created_at
                    for update of o skip locked
                    limit %s
                )
                update admin.owner_email_outbox o
                set discarded_at = %s, leased_until = null, lease_token = null
                from doomed where o.id = doomed.id returning o.id
                """,
                (now, now, batch, now),
            )
            return len(cursor.fetchall())


def prune_rate_buckets(connection, *, before: datetime, batch: int = 500) -> int:
    """Remove expired window identifiers in bounded, concurrency-safe batches."""
    before = aware(before)
    if not 1 <= batch <= 1000:
        raise ValueError("batch size must be between 1 and 1000")
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                with old as (
                    select bucket_key from admin.owner_auth_rate_bucket
                    where first_seen_at < %s
                    order by first_seen_at
                    for update skip locked
                    limit %s
                )
                delete from admin.owner_auth_rate_bucket b using old
                where b.bucket_key = old.bucket_key returning b.bucket_key
                """,
                (before, batch),
            )
            return len(cursor.fetchall())
