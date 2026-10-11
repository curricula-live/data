# Owner email outbox and durable login throttling (schema draft)

Migration `0003_owner_mail_outbox.sql` depends on data-owned
`0002_admin_owner.sql`. It adds:

- `admin.owner_auth_rate_bucket` — one hashed key per scope/time window,
  atomically incremented using `INSERT ... ON CONFLICT DO UPDATE ... WHERE`.
  No plaintext IPs, emails or raw identifiers are stored. Requires expiry
  housekeeping in later operational tooling.
- `admin.owner_email_outbox` — a unique challenge UUID per queued email,
  retry/lease fields and terminal sent/discarded timestamps. **No token or
  email content is stored in the outbox.** The worker can reconstruct the
  single-use token from the challenge UUID and a private HMAC key, then verify
  that its digest matches the stored challenge digest.

Publisher corpus and semantic releases are unaffected. PostgreSQL CI tests
idempotent migration, FK and uniqueness constraints, terminal-state safety
and atomic rate counters on a disposable database.

Do not apply to production. A separate API draft must implement an isolated
queue worker, secret rotation and controlled email dispatch. Production
activation also needs sender/reliability reviews and request-abuse controls.
