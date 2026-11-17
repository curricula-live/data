# Ontology → canonical data: incremental, evidence-first review

**Status:** Proposed integration process only. No source claims have been admitted or migrated by this branch.

## Why not import the full ontology at once?

There are independent historical and current sources with different semantics.

- `curricula-live/data` is the canonical Git-authored knowledge model. It currently contains 554 stable-ID concepts, 663 typed statements, 19 predicates and **no authored canonical definition structures**. Git publishing to PostgreSQL requires explicit review.
- `curricula-live/ontology` V1 is frozen and historically untrusted; it is **not an authorized V2 source**. The current V2 federation provides admission, scoped querying, and source-preserving contracts, but it does **not** yet certify a real, rights-cleared scientific corpus.
- A shared label such as “Array” cannot by itself establish identity between a native source URI and a canonical UUID.
- Ontology taxonomy, type membership, physical composition, reference, representation and didactic prerequisite are different relations even when they appear close in a graph.

Thus, *candidate* discovery or review prioritization is not canonical publication. This branch imports no external V1 content, copies no source prose, makes no DB changes and declares no reviews complete.

## Structural audit of the current corpus

Run the **read-only** structural checker for all 554 canonical concepts and all 663 statements:

```bash
python scripts/semantic_risk_audit.py --format markdown
python scripts/semantic_risk_audit.py --format json --output /tmp/curricula-semantic-audit.json
python scripts/semantic_risk_audit.py --concept array
python scripts/semantic_risk_audit.py --concept integer
python scripts/semantic_risk_audit.py --concept variable
```

For this version of the corpus, the structural scan found **zero directed `subtype_of` cycle groups, six direct subtype assertions with alternative multi-edge subtype paths, and nine `uses(A,B)` / `part_of(B,A)` pairs**. Zero cycles is not evidence that any subtype classification is semantically valid. Alternate paths are not necessarily incorrect or disposable; they may be deliberately materialized classifications. Paired role predicates need explicit interpretation, not automatic replacement.

The reviewed-knowledge admission procedure must preserve the original UUIDs and distinguish a structural anomaly from a scientific inconsistency. Auditing does not certify any of the 19 predicate semantics or establish source provenance.

Concept analyses are **generated on request**, not kept as one maintained Markdown file per concept. Use `python scripts/knowledge_review_queue.py --concept array` and `python scripts/semantic_risk_audit.py --concept array`; substitute `integer`, `variable`, or another canonical slug as appropriate. Reports are review aids, not accepted definitions.

## Review order

Run `python scripts/knowledge_review_queue.py --format markdown` for a deterministic, canonical-source-backed summary. JSON is available via `--format json`. For example, `python scripts/knowledge_review_queue.py --format markdown --concept array` prints every existing Array-connected statement with its exact canonical UUID, direction and predicate for manual review; it does not claim to authenticate the underlying scientific source.

The queue separates:

1. **Core, high-teaching-relevance concepts** — Array, Variable, Integer, Number, Boolean, Data, Computer, Compiler, Computer Network, Binary, Algorithm, Data Type.
2. **Supporting concepts** — Index, Collection, Data Structure, Value, Rational Number, Real Number, Program, Source Code, Bit. Some are worth incorporating before otherwise more popular concepts because they make proofs interpretable.
3. **Deferable concepts** — Color, Camera, Animation and other less-connected candidates, unless they close an essential semantic gap or supply a useful counterexample.
4. **Identity candidates absent from the canonical index** — TCP, Transport Protocol, Array Indexing. Not implicitly equivalent to labels found in an external source.

Tiers express **review order**, not scientific endorsement.

## Admission/reconciliation checklist for a single concept

For each source candidate, before any canonical change:

1. Verify the source URI, version, checksum, rights and exact extracted assertion; use the ontology V2 federation's source-admission path, **not the frozen V1 corpus**.
2. Distinguish **exact identity**, **close mapping**, **related topic** and **no mapping**. Preserve the external URI; never silently rekey the canonical concept.
3. Review predicate domain/range, direction, contextual conditions and relation meaning; a taxonomy edge is not automatically a type-inclusion assertion.
4. Check the candidate against existing assertions, detect duplicates/conflicts, and enumerate consequences for the current inference rules.
5. Request an explicit human review decision with attribution and, when relevant, a rationale for any conceptual refinement.
6. Propose a Git PR against `data/dev`; run `validate_v2.py`, tests and a publication dry run.
7. Only after review and approved release from `main` may the canonical publisher apply it to PostgreSQL.

A rejected or deferred concept still exists in the source graph. It does not need to become a canonical concept to be discoverable in an external-source atlas.

## Prototype source-node identity crosswalk

The V2 federation's real authoritative corpus has **not** yet passed source-admission review. To prepare for it without importing the frozen V1 archive, the repository provides a read-only candidate generator:

```bash
python scripts/source_identity_candidates.py \
  --input /tmp/versioned-v2-source-node-discovery.jsonl \
  --format markdown

python scripts/source_identity_candidates.py \
  --input /tmp/versioned-v2-source-node-discovery.jsonl \
  --format json --output /tmp/source-candidate-crosswalk.json
```

This is an **identity discovery contract**, not a scientific-assertion adapter. Each JSONL record contains `source_id`, `source_version`, `source_uri`, `label`, and optional `candidate_slug`, `source_checksum_sha256`, `source_locator` and `rights_status`. A valid source manifest must originate from an independently obtained/verified source; **the script itself does not fetch or certify it**.

The script rejects predicate/triple fields, duplicate native identity keys, unsupported rights claims, malformed URIs and invalid slugs. Candidate identity suggestions are labeled `lexical_label_only` or `reviewer_proposed_slug`; even an exact spelling match is **never** considered verified equality. Native source URI and version remain intact. `may_publish` and `may_import_assertions` are always false. No canonical UUID or relationship is created.

Illustrative **synthetic-only** JSONL example (not a source export and not approved evidence):

```jsonl
{"source_id":"synthetic-demo","source_version":"v0","source_uri":"https://example.invalid/array","label":"Array"}
{"source_id":"synthetic-demo","source_version":"v0","source_uri":"https://example.invalid/tcp","label":"TCP"}
```

The resulting review candidates would identify the existing canonical Array UUID by **unverified lexical similarity** and leave TCP unresolved, pending an approved identity decision. Do not feed the archived ontology V1 artifacts into this bridge: their status and the ontology repository's rules prohibit claiming them as an admitted V2 source.

## Predicate-semantics audit

All **19** controlled predicate types are currently listed as *review pending* by the report. Notably:

| Predicate | Safe interpretation until reviewed | Why a richer definition needs more |
| --- | --- | --- |
| `subtype_of` | Recorded directional classification, optionally displayed `A ⊆ B` in the provisional concept UI | Mathematical-set inclusion and programming-language type membership require distinct contexts |
| `part_of` | Recorded part–whole relation | Do not replace it with set membership `∈`; composition/containment also need explicit type and scope |
| `uses` | A recorded use relation | Does not establish necessity, accessibility, prerequisites, or equivalence |
| `represents` | Representation claim, with direction preserved | Encoding, denotation, visualization and physical realization require distinct contracts |
| `prerequisite_of` | Historical unreviewed pedagogical relation in old data | Authoritative prerequisite claims require learner context and human review in ontology V2 |

The concept-page prototype currently supports subtype transitivity conditionally on recorded assertions; that is a *UI experiment*, **not a validation of all existing `subtype_of` meanings**.

Logical `not`, `or`, `⇔` and necessary/sufficient properties cannot be mechanically recovered from an absence of edges. Design their typed models and evaluate each rule against reviewed counterexamples before enabling them.

## First proposed review dossier: Array

Current unreviewed canonical facts include classification as Collection and Data Structure, use of Index, and Index being part of Array. They are insufficient to establish a full array mathematical model, indexed-access semantics, element homogeneity or memory-contiguity properties.

A reviewed source dossier should first decide which senses of *Array*, *Index*, *Array Type* and *Array Indexing* are being modeled; next check the specialized predicates and formal specification claims. Its accepted identity decisions can then support a better structured Definition 01 and optional theorem candidates.

## What this branch does *not* do

It does not import the archived ontology; create new canonical concepts, definitions, predicates, statements or source alignments; change the database; authenticate sources; assert rights; or publish anything. The queue and report are reproducible **review aids**.
