# Database

Provider-neutral PostgreSQL migrations for the shared curricula.live domain model.

## Ownership

This repository owns shared `knowledge` and `curriculum` database structures because they are consumed by more than one service. The public API and the future `admin.curricula.live` application are consumers, not competing schema owners.

## Migration policy

- migrations are ordered, reviewed SQL under `database/migrations/`;
- migrations must remain ordinary PostgreSQL unless a provider-specific dependency is explicitly justified;
- canonical data publication never applies DDL implicitly;
- production schema changes are a separate deliberate release step with a rollback plan;
- the current host may be Supabase, Azure Database for PostgreSQL, or another compatible PostgreSQL service without changing canonical knowledge files.

`0001_knowledge_core.sql` is a target migration only until the API/database cutover is coordinated.

## Published v2 read gate

After an independently reviewed target migration and exact `publish.py verify`, apply
`0004_knowledge_release.sql` and run `python -m scripts.stamp_publication
--database-url <non-production-URL> --confirm STAMP-VERIFIED-PUBLICATION`.
The stamp records the current Git commit only when canonical files are clean and
PostgreSQL exactly matches them. Every subsequent `publish.py apply` clears it.
The public API requires `PUBLIC_V2_ENABLED=true` and
`PUBLIC_V2_RELEASE_COMMIT=<stamped 40-character commit>`, and fails closed on a
missing or mismatched stamp. Do not treat a local stamp as production parity
or permission to apply migrations to production.
