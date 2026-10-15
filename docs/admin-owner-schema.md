# Operational owner schema — staging contract

Source of truth: \`database/migrations/0002_admin_owner.sql\`.
**Not installed in production; not a knowledge publishing migration.**
All rows are operational database data, never canonical JSONL.

- \`admin.owner_principal\` permits only the \`owner\` role and has a partial
  unique index enforcing **at most one active owner**, independent of API bugs.
- \`admin.email_challenge\` holds SHA-256 purpose-bound token digests, expiry,
  and consumed-at timestamp; an API redemption must use one conditional
  UPDATE in a transaction, and test the owner is still active before issuing
  a revocable session. A GET must never consume a challenge.
- \`admin.owner_session\` holds only session token digests, expiry and
  revocation metadata; every protected API call must re-check active owner.
- \`admin.owner_audit\` has a constrained event vocabulary and no free-text
  payload for accidentally logging credentials or links.
- A one-time bootstrap command exists only for **explicit staging**:
  \`APP_ENV=staging STAGING_DATABASE_URL=... python -m scripts.bootstrap_staging_owner --email <owner@domain> --confirm BOOTSTRAP-STAGING-OWNER\`.
  It fails on any pre-existing different or disabled principal; transfer and
  deletion require a separately audited recovery procedure.
- Tests execute the SQL against a throwaway PostgreSQL 16 service in GitHub
  Actions. Unit and schema CI passing does **not** authorize production apply.

Dependency chain: [data#18](https://github.com/curricula-live/data/issues/18)
→ [api#43](https://github.com/curricula-live/api/issues/43)
→ [admin#2](https://github.com/curricula-live/admin/issues/2).
