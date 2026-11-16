# Integer — contextual semantics review

**Status:** candidate dossier; no admission or editorial approval. This document does not modify canonical knowledge.

The canonical concept `integer` currently has these four direct relationships:

| Claim UUID | Recorded statement |
| --- | --- |
| `0269fe04-0390-4d00-83ed-5c0b6b8dc0b5` | `integer subtype_of number` |
| `b581530d-9866-4ad8-94d4-b3bd049c19ab` | `integer subtype_of rational-number` |
| `c305c43e-8788-4a25-a02c-adf0381537b5` | `natural-number subtype_of integer` |
| `5369252d-ac27-445c-8620-de5b93d0eea5` | `index uses integer` |

## Why "Integer is a real number" appears

The existing graph also records:

- `rational-number subtype_of real-number`, UUID `32445633-7600-4284-af41-4a1b92e746e9`;
- `rational-number subtype_of number`, UUID `18e8d809-ab72-4ee3-a991-a828a2296fc2`;
- `number subtype_of value`, UUID `85d5d51e-80d1-462e-b194-ed287a520366`;
- `value subtype_of data`, UUID `e2f38c5d-5926-444a-9402-06ae60a1f0d5`.

If every concept here names its **mathematical extension**, the chain

`Integer ⊆ Rational Number ⊆ Real Number`

is an ordinary mathematical inclusion. However, if `Integer` and `Real Number` are **programming-language data types**, this inference need not hold: the runtime representations, value domains, coercions and subtyping semantics may differ. A lexical label cannot settle which sense is represented.

The structural auditor also finds a direct `integer subtype_of number` assertion that has an alternative two-step path through `rational-number`. This is **not necessarily an error**: redundant explicit ontology assertions may be useful for retrieval, but must be distinguished from derived consequences.

## Review questions

1. Is this canonical identity a mathematical set of integers, a programming-language integer type, or an educational umbrella topic?
2. If it is the mathematical concept, which model of reals and rationals is intended? Can `⊆` be used, and is transitivity valid in that scoped model?
3. If it is a programming-language type, are type widening, implicit conversions, representation and subtype membership separate predicates?
4. Does the source actually support `index uses integer` for all indexing schemes, or only for conventional array/sequence indices?
5. Should `number subtype_of value` and `value subtype_of data` be understood as mathematical inclusion, type taxonomy, or informal representation? The resulting `integer subtype_of data` is especially likely to cross scopes.

## Proposed *model* (not a canonical claim)

A future typed-claim contract could separately represent:

- `scope: mathematics / set-membership / ℤ`, `scope: programming / integer-type / language-specific`;
- explicit definitions of `IntegerSet` and `IntegerType(L)`;
- source-linked `necessary`, `sufficient`, and `equivalent` conditions;
- proof witnesses that require matching scopes for every premise.

**No new concept IDs or edges are proposed for publication in this dossier.** Do not infer from labels or rename the existing canonical Integer silently. Audit Array, Number, Rational Number, Real Number, Value and Data together before approving rules.

Reproduce the structural findings:

```bash
python scripts/semantic_risk_audit.py --concept integer
python scripts/knowledge_review_queue.py --concept integer
```
