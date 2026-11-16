# Array — first semantic review dossier

**Status:** research draft, awaiting approved sources and human acceptance  
**Canonical concept:** `array` (existing UUID; do not change identity)  
**Source of the observations below:** existing `curricula-live/data/knowledge/statements.jsonl`; these are **not independently verified scientific assertions**.

This dossier is not a new definition, a migration, a change to a predicate, or approval to publish a graph. It specifies what a reviewer would need to establish before stronger Array documentation can be generated.

## 1. Recorded hypotheses

| Reference | Existing statement UUID | Subject | Predicate | Object |
| --- | --- | --- | --- | --- |
| h1 | `048adf33-0701-43de-998f-20c299388f51` | Array | subtype_of | Collection |
| h2 | `415c675b-d455-4282-a868-d630f3e47381` | Array | subtype_of | Data Structure |
| h3 | `4962d9c0-b958-449d-aebd-993b88dcdd01` | Array | uses | Index |
| h4 | `307da941-512a-404e-9ea6-f8470a645e13` | Index | part_of | Array |

The strictly mechanical conjunction is:

```text
subtype_of(Array, Collection)
AND subtype_of(Array, DataStructure)
AND uses(Array, Index)
AND part_of(Index, Array)
```

No `OR`, `NOT`, `IFF`, `accessed_by`, `has_index_domain`, `requires_prior_knowledge_of` or mathematical `A : I -> T` premise is licensed by these four edges alone.

## 2. Conditional consequences currently derivable

**Candidate Proposition 01:** `Array ⊆ Data`  
Premises: h1; `Collection subtype_of Data` (UUID `15ead31d-e970-4aad-a4f8-7c9fccf3097a`).  
Rule proposal: transitivity of `subtype_of`.

**Candidate Proposition 02:** `Array ⊆ Structure`  
Premises: h2; `Data Structure subtype_of Structure` (UUID `66ca0673-181a-4c01-b0ba-2ada328a52b9`).  
Rule proposal: transitivity of `subtype_of`.

These are **conditional proof paths on recorded classifications**. They are not verified mathematical theorems or accepted scientific assertions. The reviewer must first establish that each edge uses the same semantic interpretation of `subtype_of`, such that transitivity is sound.

## 3. Open semantic decisions

1. **Class versus instance:** Does `Array subtype_of Collection` express a subsumption relation among kinds, or membership of array objects in collections? Does `⊆` mislead when the concepts are not modeled as extensions of classes? A formal type hierarchy can use `⊑` while mathematical set inclusion can use `⊆`.
2. **Indexed access:** `uses(Array, Index)` is too weak to establish that array elements are *accessed by an index*. Should the source support a more precise `indexed_by`, `accessed_by`, or functional-relation assertion? Do not add the new predicate until its domain/range, direction and context have been reviewed.
3. **Part–whole claim:** What exactly does `part_of(Index, Array)` mean? Is the *set of valid indices* modeled as part of the array abstraction, or is an individual *index* a literal part of an array value? Should it instead connect an `Index Domain` to a formal Array model? An apparently reasonable English paraphrase can conceal a category error.
4. **Formal model:** `A : I → T` is plausible in an abstract mathematical model of arrays only after explicit evidence establishes a domain `I`, an element codomain `T`, totality and one value per index. It does **not** on its own establish contiguous memory, O(1) operations, fixed length or zero-based indices.
5. **Context:** Separate a general Array abstract data structure, array data types in specific languages, and physical array representations before deriving claims about mutability, storage layout, memory addressing or bounds.
6. **Source/admission:** Identify an authorized, attributable source URI and version for each candidate claim. The archived V1 ontology alone is insufficient to certify it; do not copy source text across licensing boundaries.

## 4. Related concepts in the first review wave

`Collection`, `Data Structure`, `Index`, `Data` and `Structure` are directly relevant for the two displayed subtype proofs. The concepts `Array Indexing`, `Array Type`, `One-dimensional Array` and `Dynamic Array` may provide necessary distinctions, but each must pass the canonical identity mapping and source-rights gates before admission.

**Important:** A less broadly taught concept can be promoted in review priority when it removes ambiguity from a central proof. Popularity is not the only relevance measure.

## 5. Suggested acceptance checks (none completed yet)

- [ ] Confirm exact identity and sense of Array, Collection, Index and Data Structure.
- [ ] Confirm source rights, version and locator for every accepted assertion.
- [ ] Specify `subtype_of` domain/range, context and permitted transitive behavior.
- [ ] Decide whether h3 and h4 should remain, be narrowed, or be replaced with reviewed specific predicates.
- [ ] Identify and verify formal model claims independently of existing `uses` relationships.
- [ ] Recompute proof witnesses and compare old/new derived conclusions under approved semantics.
- [ ] Add positive and negative fixtures: zero-based vs one-based, dynamic vs static, logical vs memory representation.
- [ ] Submit a separately reviewed change to canonical Git data if warranted. No database write or production release before explicit authorization.

### Reproduction

```bash
python scripts/knowledge_review_queue.py --format markdown --concept array
python scripts/knowledge_review_queue.py --format json --output /tmp/concept-review-dossiers.json
python scripts/validate_v2.py
pytest -q
```

The generated dossier is reproducible and records exact UUIDs; the research questions above are **review proposals**, not facts introduced into the canonical corpus.
