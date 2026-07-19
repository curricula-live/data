# Agent instructions

## Scope

This repository is the deterministic, reviewable interchange format for the curricula.live graph. Supabase remains the runtime database.

## Invariants

- Keep `data/concepts.jsonl` and `data/relations.jsonl` deterministic and one-record-per-line.
- Concept references in relation files use slugs, never database UUIDs.
- A concept slug is its canonical immutable identity. A slug change is a reviewed delete/create operation.
- Relation predicates are extensible lowercase snake_case strings. Do not introduce a closed enum.
- `push` must remain plan-only unless `--apply` is explicitly supplied.
- Pruning must remain opt-in and require the exact additional confirmation `DELETE`.
- Never commit connection strings or Supabase credentials.
- Do not use the small seed dataset as an authoritative production snapshot. A full pull from Supabase must happen before pruning is enabled.

## Validation

Run before proposing changes:

```bash
python scripts/sync.py check --format
pytest -q
```

## Workflow safety

- Pulling from Supabase may create a reviewable PR automatically.
- Pushing to Supabase must remain manual and use the protected `supabase-production` environment.
- Avoid third-party GitHub Actions when the same behavior can be implemented with the GitHub CLI and the repository token.
