# curricula.live data

Canonical, reviewable source for the curricula.live knowledge system.

Git is the publishing authority. PostgreSQL is a runtime projection of reviewed repository state. The current runtime happens to be hosted by Supabase, but the model, migrations, and publisher use ordinary PostgreSQL so the runtime can later move to another PostgreSQL service without changing the knowledge model.

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
publication plan
      ↓
approved database publish
      ↓
PostgreSQL runtime
      ↓
verification
      ↓
API
```

`main` represents published canonical state. Direct production-database editing is not the normal authoring workflow. Database drift is reported; it is never pulled back automatically into canonical Git.

## Repository layout

```text
knowledge/      canonical concepts, predicates, statements and definitions
curriculum/     mappings from external curricula to canonical knowledge
database/       provider-neutral PostgreSQL migrations and schema notes
migration/      historical/reproducible migrations into canonical Git
pipeline/       extraction/reconciliation contract; inputs are non-canonical
schema/         JSON Schemas for canonical repository records
scripts/        validation, migration and publication tooling
tests/          repository contract tests
```

There is intentionally no nested `data/data` canonical layout.

## Core invariants

### Stable identity

Canonical concepts use stable UUIDs. Human-readable slugs are unique lookup/URL keys, not immutable identity. A slug may change without changing the concept.

The original production graph was captured into v2 Git using a deterministic one-time UUID migration. That historical mapping is retained under `migration/legacy-v1/`. New concepts receive stable UUIDs directly; their UUIDs are never regenerated from later slug changes.

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
pytest -q
```

## Database publication

The canonical publisher is one-way:

```bash
python scripts/publish.py plan
python scripts/publish.py apply --confirm-publish PUBLISH
python scripts/publish.py verify
```

All commands use `DATABASE_URL`. The publisher targets the shared `knowledge` schema and does not apply DDL automatically.

Production publication is exposed through the manual GitHub Actions workflow **Publish canonical data to PostgreSQL**. Configure a protected GitHub environment named `production-database` with a `DATABASE_URL` secret and required reviewers. Production `apply` is accepted only from `main`.

Database migrations remain a separate reviewed release step. The current v2 target migration must not be applied to production until the API/database cutover phase is coordinated.

## Legacy migration

The previous Supabase-first snapshot/synchronization workflow is retired. The historical exporter and identity ledger remain under `migration/legacy-v1/` and `scripts/migrate_legacy.py` so the origin of the initial canonical UUID-backed corpus stays reproducible and auditable.

Never commit database credentials, private source documents, or user/admin secrets.
