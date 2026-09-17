# Agent instructions

## Scope

This repository is the canonical, reviewable source for the curricula.live knowledge system and its shared provider-neutral PostgreSQL domain schema.

Git `main` is the publishing authority. PostgreSQL is a runtime projection. Do not treat Supabase or any other database host as the canonical authoring surface.

## Naming

- Use full, readable namespace names. Use `knowledge`, never `kg`.
- Prefer simple, explicit names over abbreviations or generic metadata bags.
- Keep school-system/provider terminology out of canonical knowledge records unless it belongs to the separate `curriculum` overlay.

## Knowledge invariants

- Canonical concepts have stable UUID identities.
- `slug` is a unique human-readable key and URL handle, not immutable identity.
- Do not add a generic `description` field to concepts or other entities as a shortcut for modelling factual meaning.
- Express factual meaning through explicit typed statements.
- Statements have stable UUIDs and may reference concepts or other statements.
- Keep the predicate vocabulary small, readable and extensible; add a predicate only when an existing one cannot express the fact cleanly.
- A concept has at most one canonical definition structure, composed from canonical statements.
- Do not create level-specific definitions such as `primary`, `basic`, or `formal`; level belongs in curriculum mapping and presentation belongs in consuming products.

## Curriculum and ingestion boundary

- Canonical knowledge is independent of Cambridge, Pearson, IB, College Board, OxfordAQA, national curricula, Wikidata, and other external systems.
- External documents are ingestion/reconciliation inputs, not canonical knowledge records.
- Do not commit syllabus PDFs or copied source prose into the canonical knowledge directories.
- Curriculum placement belongs under `curriculum/`, never as generic concept-to-concept relations.
- Candidate extraction output is non-canonical until reconciled and reviewed.

## Database invariants

- Shared domain migrations live under `database/`.
- Use ordinary PostgreSQL and avoid host-specific APIs/extensions unless explicitly justified.
- The shared domain schemas begin with `knowledge` and `curriculum`.
- The future `admin` schema is operational: identity, authorization, audit and review records must not be serialized into canonical public knowledge files.
- Do not apply v2 migrations to production until coordinated API compatibility work is reviewed.

## Repository workflow

- Branch from `dev` for normal work.
- Merge feature PRs to `dev`.
- Promote `dev` to `main` through an explicit release PR.
- `main` is the only branch that may be treated as published canonical knowledge.

## Legacy transition

The existing `data/`, `schema/concept.schema.json`, `schema/relation.schema.json`, and `scripts/sync.py` describe the v1 Supabase-first interchange format. Keep them working until the production corpus and API have migrated, but do not extend them for new v2 modelling.

## Validation

Run before proposing changes:

```bash
python scripts/validate_v2.py
python scripts/sync.py check --format
pytest -q
```

Never commit database credentials, service tokens, private source documents, or user/admin secrets.
