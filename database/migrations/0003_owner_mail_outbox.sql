-- Operational email delivery / throttling v0.1. Staging migration only.
-- Never stores raw passwordless email links, bearer tokens, source IPs, or email addresses.
-- Depends on 0002_admin_owner.sql. No production application is authorized.
create table if not exists admin.owner_auth_rate_bucket (
    bucket_key text primary key,
    attempts integer not null default 1,
    first_seen_at timestamptz not null default now(),
    constraint owner_auth_rate_bucket_hash check (bucket_key ~ '^[0-9a-f]{64}$'),
    constraint owner_auth_rate_bucket_attempts check (attempts between 1 and 10000)
);
create index if not exists owner_auth_rate_bucket_created_idx
    on admin.owner_auth_rate_bucket (first_seen_at);

create table if not exists admin.owner_email_outbox (
    id uuid primary key,
    challenge_id uuid not null unique
        references admin.email_challenge(id) on delete restrict,
    created_at timestamptz not null default now(),
    available_at timestamptz not null default now(),
    leased_until timestamptz,
    attempts integer not null default 0,
    delivered_at timestamptz,
    discarded_at timestamptz,
    constraint owner_email_outbox_attempts check (attempts between 0 and 5),
    constraint owner_email_outbox_final_state check (
        not (delivered_at is not null and discarded_at is not null)
    )
);
create index if not exists owner_email_outbox_pending_idx
    on admin.owner_email_outbox (available_at, id)
    where delivered_at is null and discarded_at is null;

comment on table admin.owner_auth_rate_bucket is
    'Hashed, window-scoped rate limit keys; no raw IP or email values.';
comment on table admin.owner_email_outbox is
    'Queued challenge UUIDs only; worker derives the link from secret material at send time.';
