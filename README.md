# curricula.live data

Version-controlled interchange format for the curricula.live concept graph.

Supabase PostgreSQL is the runtime database. This repository provides deterministic JSONL snapshots so graph changes can be reviewed through Git and pull requests. It is not a second independently writable database.

## Files

- `data/concepts.jsonl` — one concept per line
- `data/relations.jsonl` — one typed relation per line, using concept slugs
- `schema/` — JSON Schema definitions
- `scripts/sync.py` — validation and synchronization CLI

The committed queue records are only an initial format example. Run the pull workflow to replace them with the complete current Supabase snapshot before considering pruning.

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

Manual workflow that exports the full database snapshot and opens a reviewable pull request when data changed.

### Plan or push graph to Supabase

Manual workflow attached to the `supabase-production` environment. It defaults to plan-only mode. Applying changes is explicit, and pruning additionally requires the exact confirmation `DELETE`.

Configure the repository or environment secret:

```text
SUPABASE_DATABASE_URL
```

For production use, configure required reviewers on the `supabase-production` GitHub environment.
