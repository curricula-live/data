# Shared PostgreSQL domain schema

This directory owns the provider-neutral PostgreSQL schema used by curricula.live domain services.

The public API is a consumer of this schema, not its sole owner. The future `admin.curricula.live` service will also consume the shared knowledge/curriculum model.

## Schemas

- `knowledge` — canonical concepts, predicates, statements and definition membership;
- `curriculum` — curriculum overlays and mappings (tables intentionally deferred until the mapping model is validated);
- `admin` — reserved operational namespace for authenticated administration, authorization, audit and review records. Admin rows are runtime operational data and are not serialized into canonical knowledge JSONL.

## Portability

Migrations must use ordinary PostgreSQL. Supabase is the current host, not an architectural dependency. Avoid Supabase-specific APIs, triggers or extensions unless a reviewed migration documents a concrete need.

## Migration policy

Migrations are append-only and ordered. `0001_knowledge_core.sql` describes the target v2 core **but is not yet approved for production application**.

The current production database still uses the legacy `public.concept`, `public.relation_type`, and `public.relation` contract. A coordinated migration must:

1. export/reconcile the production corpus into canonical UUID-backed Git records;
2. update the API to resolve concepts by UUID internally while preserving slug-based public URLs;
3. migrate production data into the new schemas;
4. verify reads and search;
5. only then retire legacy public tables/synchronization.

Do not run v2 migrations directly against production ahead of that coordinated release.
