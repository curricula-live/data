# Ontology → canonical data: incremental, evidence-first review

**Status:** Proposed integration process only. No source claims have been admitted or migrated by this branch.

## Why not import the full ontology at once?

There are independent historical and current sources with different semantics.

- `curricula-live/data` is the canonical Git-authored knowledge model. It currently contains 554 stable-ID concepts, 663 typed statements, 19 predicates and **no authored canonical definition structures**. Git publishing to PostgreSQL requires explicit review.
- `curricula-live/ontology` V1 is frozen and historically untrusted; it is **not an authorized V2 source**. The current V2 federation provides admission, scoped querying, and source-preserving contracts, but it does **not** yet certify a real, rights-cleared scientific corpus.
- A shared label such as “Array” cannot by itself establish identity between a native source URI and a canonical UUID.
- Ontology taxonomy, type membership, physical composition, reference, representation and didactic prerequisite are different relations even when they appear close in a graph.

Thus, *candidate* discovery or review prioritization is not canonical publication. This branch imports no external V1 content, copies no source prose, makes no DB changes and declares no reviews complete.

## Review order

Run `python scripts/knowledge_review_queue.py --format markdown` for a deterministic, machine-readable-source-backed summary. JSON is available via `--format json`.

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
