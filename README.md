# curricula.live data

Canonical, reviewable source for the curricula.live knowledge system.

Git is the publishing authority. PostgreSQL is a runtime projection of reviewed repository state. The current runtime happens to be hosted by Supabase, but the model and migrations must remain ordinary PostgreSQL so the system can move to another PostgreSQL service without changing the knowledge model.

## Canonical flow

```text
editor/admin change
      ↓
feature branch
      ↓
pull request
      ↓
validation + review
      ↓
dev
      ↓
release review
      ↓
main
      ↓
publish/migrate
      ↓
PostgreSQL runtime
      ↓
API
```

`main` represents published canonical state. Direct production-database editing is not the normal authoring workflow.

## Repository layout

```text
knowledge/      canonical concepts, predicates, statements and definitions
curriculum/     mappings from external curricula to canonical knowledge
database/       provider-neutral PostgreSQL migrations and schema notes
pipeline/       extraction/reconciliation workflow; inputs are non-canonical
schema/         JSON Schemas for canonical repository records
scripts/        validation and transition tooling
tests/          repository contract tests
```

The existing `data/` directory and `scripts/sync.py` are **legacy v1 compatibility surfaces**. They remain temporarily while the current API/database contract is migrated. New v2 authoring must not extend that format.

## Core invariants

### Stable identity

Canonical concepts use stable UUIDs. Human-readable slugs are unique lookup/URL keys, not immutable identity. A slug may change without changing the concept.

### No generic descriptions

Concept records do not contain a catch-all `description` field. A concept is identified minimally by UUID, slug and label. Factual meaning belongs in explicit statements and definition structures.

### Statement-first knowledge

Canonical factual knowledge is represented by typed statements. Statements have UUIDs and may reference concepts or other statements, allowing relationships between relationships without requiring a graph-database product.

Literals are permitted where a fact genuinely contains a value. They are not a substitute for semantic relationships.

### One canonical definition

A concept may have one canonical definition structure composed from selected canonical statements. Educational levels do not create parallel `basic`, `primary`, or `formal` definitions. Curriculum tells us **where** a concept is taught; presentation layers decide **how** to explain it for a particular audience.

### Curriculum independence

Canonical knowledge is not owned by Cambridge, Pearson, IB, College Board, OxfordAQA, a national curriculum, Wikidata, or any other external system.

External syllabi and references may be used as ingestion/reconciliation inputs. Their documents and wording are not canonical knowledge and are not copied into the public knowledge model. Curriculum-specific placement is stored only in the separate `curriculum` overlay.

### Portable PostgreSQL

Shared domain schemas use readable full names such as `knowledge` and `curriculum`, never abbreviations such as `kg`. Avoid provider-specific database features unless a reviewed migration documents why they are necessary.

## Development flow

Create feature branches from `dev` and merge reviewed work back into `dev`. Promote `dev` to `main` through an explicit release pull request.

Before proposing changes:

```bash
python scripts/validate_v2.py
python scripts/sync.py check --format  # legacy transition contract
pytest -q
```

## Current transition

The production runtime currently contains substantially more knowledge than the small v1 repository seed. The v2 migration will first reconcile the runtime corpus into stable UUID-backed canonical repository records, then coordinate the API schema migration, and only then retire the legacy Supabase-first synchronization path.
