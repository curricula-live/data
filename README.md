# curricula.live data

Version-controlled interchange format for the curricula.live concept graph.

Supabase PostgreSQL is the runtime database. This repository provides deterministic JSONL snapshots so graph changes can be reviewed through Git and pull requests. It is not a second independently writable database.

Concept slugs are the canonical, immutable repository identities. Supabase UUIDs are runtime implementation details and are resolved from slugs during synchronization. Changing a slug intentionally means deleting one concept and creating another; it is not a rename that preserves identity.

## Files

- `data/concepts.jsonl` — one concept per line
- `data/relations.jsonl` — one typed relation per line, using concept slugs
- `data/snapshot.json` — machine-checkable proof that JSONL files came from one complete pull
- `schema/` — JSON Schema definitions
- `scripts/sync.py` — validation and synchronization CLI

The committed queue records are only an initial format example. They cannot be used for pruning. A full pull creates a marker containing exact row counts and SHA-256 hashes; pruning fails closed if that marker is absent, invalid, or stale.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql://...'
```

## Commands

```bash
# Validate schemas, duplicate keys, references, and relation predicates
python scripts/sync.py check

# Also verify deterministic ordering and compact JSON formatting
python scripts/sync.py check --format

# Rewrite JSONL deterministically
python scripts/sync.py format

# Replace local JSONL with the current Supabase graph
python scripts/sync.py pull

# Compare Git data with Supabase without writing
python scripts/sync.py plan

# Plan only; no database writes without --apply
python scripts/sync.py push

# Upsert concepts and relations without deleting anything
python scripts/sync.py push --apply

# Destructive synchronization; requires two explicit signals
python scripts/sync.py push --apply --prune --confirm-prune DELETE
```

## GitHub Actions

### Validate graph data

Runs on every pull request and validates schemas, references, deterministic formatting, and tests.

### Pull graph from Supabase

Runs on `repository_dispatch` (`supabase_graph_changed`), manual dispatch, and a daily reconciliation schedule. It exports the full database snapshot and creates or updates one reviewable pull request only when data changed. The API should use dispatch as the primary trigger; the schedule is only reconciliation.

### Plan or push graph to Supabase

Manual workflow attached to the `supabase-production` environment. It defaults to plan-only mode. Applying changes is explicit, and pruning additionally requires the exact confirmation `DELETE`.

Configure the repository or environment secret:

```text
SUPABASE_DATABASE_URL
```

For production use, configure required reviewers on the `supabase-production` GitHub environment.

Recommended setup:

- `supabase-staging`: staging database URL; use it for the first pull, plan, and non-destructive apply verification.
- `supabase-production`: production database URL with required reviewers; do not enable pruning until a full snapshot PR has been reviewed and merged.

Recovery is Git-based: stop apply workflows, pull a fresh snapshot into a PR, compare it with the last known-good commit, and apply only after review. Never restore by enabling prune against an incomplete or hand-edited snapshot marker.
