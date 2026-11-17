# Exhaustive source relationship reconciliation (unreviewed)

This is the **source candidate layer**, separate from canonical
`knowledge/concepts.jsonl`, `knowledge/predicates.jsonl`, and
`knowledge/statements.jsonl`. It is NOT a declaration of scientific truth.

Two archived/user-originated sources have been completely processed:

| Corpus | Source URI assertions reconciled | Predicate proposals |
|---|---:|---:|
| Official CSO 3.5, CC BY 4.0 | 151,882 | 8 |
| Frozen curricula.live historical V1 | 2,081 | 6 |
| **Total** | **153,963** | **14** |

CSO also has 14,636 English label triples preserved in its exact original ZIP.
Only URI-object triples enter the source assertion staging tables. The data
manifest records the full 166,518 CSO N-Triples line count.

## Deterministic candidate mappings

- The original 1,856 historical identity proposals exist on the feature
  branch, but have not been approved in a canonical release.
- All **2,081** historical source relations were mapped and classified.
  **1,742** have draft UUID references on BOTH ends, **336** require approval
  of exact-label existing concept matches, and **3** are blocked due to
  ambiguous identity collisions.
- **1,854 / 1,856** new identities have at least one historical relation
  candidate. The remaining two have explicit zero-coverage records, not
  invented edges.
- All **151,882** CSO URI relations retain full native predicate IRIs,
  original source URIs and a SHA-256 witness. Exact-label overlap only
  produces unapproved identity candidates; never an implicit `sameAs`.
- All 14 predicate mappings are source-qualified and `inference_eligible:
  false`. `broaderTopic` and `superTopicOf` are topic hierarchies, not
  `subtype_of`, and source links do not imply educational prerequisites.
- The generated legacy `proposed_statement` objects are a review queue,
  **not records in `knowledge/statements.jsonl`**.

## Review and reproducibility

```sh
python scripts/reconcile_source_relations.py
python scripts/review_source_concept.py binary-tree --limit 8
python scripts/review_source_concept.py tcp --limit 8
python scripts/source_coverage_search.py 'TCP'
python scripts/validate_v2.py
pytest -q
```

The canonical statement store remains at **663** records (all existing);
canonical predicate count remains **19**. The new source data can be queried
without changing trusted subtype-inference premises.

## Optional local-only PostgreSQL source staging

An independent, provider-neutral **`knowledge_source`** schema is defined
in `database/migrations/0002_source_reconciliation_staging.sql`. This
is distinct from authoritative `knowledge` and includes database CHECK
constraints forbidding `inference_eligible=true` on source predicates and
assertions.

The explicit loader refuses remote PostgreSQL hosts and database names that
look like production databases. Apply it **only to disposable local PostgreSQL**:

```sh
export DATABASE_URL='postgresql://local_user@127.0.0.1:5432/local_review_db'
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0002_source_reconciliation_staging.sql
python scripts/stage_source_reconciliation.py plan
python scripts/stage_source_reconciliation.py apply \
  --confirm-staging STAGE-UNREVIEWED-SOURCES
python scripts/stage_source_reconciliation.py verify
```

Expected: two corpora, **16,637** labelled topics, **14** native predicate
mappings, **153,963** staged source assertions. A reproducible local test
published, verified and re-published all records with no `knowledge`
schema present. No production database was changed.

The companion API draft exposes staging-gated read-only source search,
relation neighborhood and predicate vocabulary endpoints. Their responses
declare `canonical_identity_approved=false` and
`inference_eligible=false`, and the routes remain unavailable in production.

## Promotion gates

Approval must happen *before* any source claim enters the canonical
`knowledge/statement` table and before the inference engine relies on it:

1. Verify source/target identity, including collisions, aliases and context.
2. Review predicate meaning, direction, domain, range and whether the
   source is expressing taxonomy, a mechanism, a reference or a theorem.
3. Record exact source evidence and scope, plus reviewer and decision.
4. Verify licensing and distinguish source claims from proven consequences.
5. Only then authorize a canonical statement or inference rule in a
   separately reviewed PR.

No amount of corpus size, algorithmic matching or passing tests can bypass
these gates automatically.
