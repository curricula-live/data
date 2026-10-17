-- curricula.live operational owner identity v0.1
-- STAGING-TARGET MIGRATION ONLY. Do NOT apply to production without a
-- separately authorized database migration and rollback plan.
-- This schema is operational, never Git-canonical knowledge.
create schema if not exists admin;

create table if not exists admin.owner_principal (
    id uuid primary key,
    email text not null,
    role text not null default 'owner',
    active boolean not null default true,
    created_at timestamptz not null default now(),
    disabled_at timestamptz null,
    constraint owner_role_exact check (role = 'owner'),
    constraint owner_email_format check (
        email = lower(btrim(email))
        and email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
        and length(email) between 3 and 320
    ),
    constraint owner_active_disabled_consistency check (
        (active and disabled_at is null) or (not active and disabled_at is not null)
    )
);
-- A single active owner regardless of email. Historic disabled rows are retained.
create unique index if not exists owner_single_active_idx
    on admin.owner_principal (role) where active;
-- Prevent silent reusing the same identity with another principal.
create unique index if not exists owner_email_lower_idx
    on admin.owner_principal (lower(email));

create table if not exists admin.email_challenge (
    id uuid primary key,
    owner_id uuid not null references admin.owner_principal(id) on delete restrict,
    token_hash text not null unique,
    issued_at timestamptz not null default now(),
    expires_at timestamptz not null,
    consumed_at timestamptz null,
    constraint email_challenge_hash_format check (token_hash ~ '^[0-9a-f]{64}$'),
    constraint email_challenge_expiry_check check (expires_at > issued_at),
    constraint email_challenge_consumption_check check (
        consumed_at is null or consumed_at >= issued_at
    )
);
create index if not exists email_challenge_pending_idx
    on admin.email_challenge (owner_id, expires_at) where consumed_at is null;

create table if not exists admin.owner_session (
    id uuid primary key,
    owner_id uuid not null references admin.owner_principal(id) on delete restrict,
    token_hash text not null unique,
    issued_at timestamptz not null default now(),
    expires_at timestamptz not null,
    revoked_at timestamptz null,
    constraint owner_session_hash_format check (token_hash ~ '^[0-9a-f]{64}$'),
    constraint owner_session_expiry_check check (expires_at > issued_at),
    constraint owner_session_revocation_check check (
        revoked_at is null or revoked_at >= issued_at
    )
);
create index if not exists owner_session_active_idx
    on admin.owner_session (owner_id, expires_at) where revoked_at is null;

create table if not exists admin.owner_audit (
    id bigint generated always as identity primary key,
    owner_id uuid null references admin.owner_principal(id) on delete restrict,
    event_type text not null,
    occurred_at timestamptz not null default now(),
    request_id uuid null,
    constraint owner_audit_event_known check (event_type in (
        'owner_bootstrapped', 'owner_disabled',
        'challenge_issued', 'challenge_redeemed', 'challenge_denied',
        'session_created', 'session_verified', 'session_revoked',
        'access_denied'
    ))
);
create index if not exists owner_audit_timestamp_idx on admin.owner_audit (occurred_at desc);

comment on table admin.owner_principal is
    'Single active owner principal; identity rows are operational, not Git-canonical.';
comment on table admin.email_challenge is
    'One-use email challenge token digests only, never raw magic-link tokens.';
comment on table admin.owner_session is
    'Revocable opaque bearer session digests; API rechecks owner status on every access.';
comment on table admin.owner_audit is
    'Constrained, sanitized event metadata; no token, email or unreviewed arbitrary JSON.';
