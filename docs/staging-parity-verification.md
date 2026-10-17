# Read-only legacy → v2 PostgreSQL staging parity

This is a **release gate**, not a migration or permission to deploy.

The initial 554 concepts, 19 predicates and 663 original statements must
survive v1 → v2 migration with their identities and source–predicate–target
relations preserved. Git/unit CI verifies the corpus, but **does not establish
parity against an independently sourced legacy PostgreSQL database**.

## Requirements for an actual staging verification

An operator must independently confirm:

- A dedicated **non-production**, independently sourced staging snapshot
  contains the original `public.*` legacy tables and published `knowledge.*` v2 tables.
- The database role is **SELECT-only**, with no DDL/write privileges.
- The Git checkout uses the reviewed SHA, with a clean canonical corpus and ledgers.
- The database and PostgreSQL role were confirmed outside this tool. Matching
  their names cannot by itself prove a target is not production.

## Verify and capture evidence

Run on the pinned commit, using a restricted, encrypted evidence directory
outside Git. Never commit or print database credentials.

```bash
git rev-parse HEAD
# Confirm the staging target independently; never use the production database.
export STAGING_DATABASE_URL='postgresql://REDACTED/STAGING_DATABASE'
python -m scripts.verify_staging_parity \
  --require-v2 \
  --expected-database 'ACTUAL_STAGING_DATABASE_NAME' \
  --expected-role 'ACTUAL_SELECT_ONLY_ROLE' \
  --expected-git-sha "$(git rev-parse HEAD)" \
  --evidence-out '/secure/evidence/atlas-staging-parity-001.json'
```

The evidence file is created exclusively with mode `0600`, never overwritten.
No evidence is generated if v2 is missing or differs from Git; any historical
UUID or triple differs; the checked-out SHA or corpus is different; the database
name or role differs; or the transaction is not read-only.

The certificate includes its format version, UTC verification time, full Git
commit, SHA-256 of the canonical files and migration ledgers, checked database
name and role, verified counts, and v2 readback parity. It contains **no DSN
or password** and never contains owner tokens.

**The certificate is not a cryptographic signature or independent proof of
database provenance.** Retain the independently sourced staging snapshot
record, reviewed migration and rollback evidence, public API compatibility
tests, and explicit owner approval before production promotion.

## Exploratory (no attestation)

```bash
STAGING_DATABASE_URL='postgresql://REDACTED/STAGING_DATABASE' \
  python -m scripts.verify_staging_parity --require-v2
```

The verifier operates inside a PostgreSQL `READ ONLY, REPEATABLE READ`
transaction. It never applies DDL or data changes, merges Git branches,
publishes a release, or deploys an application.

## Optional protected GitHub Actions execution

The repository also defines `Manual staging parity evidence (read-only)`.
It can be started **only manually**, from the reviewed `dev` commit, with
confirmation `READ_ONLY_STAGING_PARITY` and the expected database/role.

Before the first run, a repository administrator must separately configure
the protected GitHub environment `knowledge-staging` with required reviewer
approval and its environment-only secret `STAGING_PARITY_DATABASE_URL`.
That secret must identify an independently sourced non-production snapshot
through a database role with SELECT privileges only. The workflow does not
create an environment, provision a database, or acquire credentials.

After an approved and successful run it uploads a private JSON evidence artifact
retained for 14 days. Record the source snapshot/provenance separately; GitHub
test logs and this attestation do not independently establish it. Do not run
the workflow against production or interpret passing CI as production approval.
