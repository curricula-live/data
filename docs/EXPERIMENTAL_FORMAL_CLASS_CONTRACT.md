# Experimental formal class-expression contract

**Status:** syntax prototype only. This is not a public language guide, approved
scientific definition, new canonical knowledge record, or database migration.

The canonical `knowledge/definitions.jsonl` contract remains unchanged.
Its records still reference existing canonical statements. The new file
`schema/knowledge/formal-class-model.v0.schema.json` only describes **separate
synthetic fixtures**, and cannot be published by `scripts/publish.py`.

## Shape

A model contains a stable subject concept UUID, an explicit modeling scope, a
relation (`necessary` or `equivalent`), a typed expression, and
`provenance.status = synthetic_fixture`. Referenced UUIDs must exist in the
supplied identity registry; predicate names must exist in the supplied
predicate registry. Passing validation establishes only structural correctness,
not truth, source quality, or logical consequences.

| Operator | Shape | Class-description-logic reading |
| --- | --- | --- |
| `concept` | `{op, concept_id}` | Named class |
| `and` | `{op, args:[A,B,...]}` | Intersection, `A ⊓ B` |
| `or` | `{op, args:[A,B,...]}` | Union, `A ⊔ B` |
| `not` | `{op, arg:A}` | Complement, `¬A` |
| `some` | `{op, property:R, filler:C}` | Existential role restriction `∃R.C` |
| `only` | `{op, property:R, filler:C}` | Universal role restriction `∀R.C` |

A `necessary` model produces the axiom `Subject ⊑ Expression`. An
`equivalent` model produces `Subject ≡ Expression`. The latter is a much
stronger scientific claim and cannot be inferred from a conjunction of
recorded `uses` edges.

This is **class-expression syntax**, not full first-order logic, Lean,
ring axiomatization, or proof certification. Variables, quantification over
individuals, equality, typed terms, propositions and proof objects need
separate typed contracts. The grammar was inspired by studying the historical
`ontology/native-v2` formal structures; its old scientific assertions were
**not** imported into canonical `data`.

## Synthetic test only

```bash
python scripts/validate_formal_class_model.py tests/fixtures/formal-array.synthetic.json
pytest -q tests/test_formal_class_model.py
```

The example uses known **identity references** for Array, Data Structure and
Index and a registered predicate name, but asserts no accepted statement.
It illustrates a possible `Array ⊑ (DataStructure ⊓ ∃uses.Index)` structure,
**not a claim justified by the existing Array relation records**.

A second pure API helper, `core/formal_class_inference.py`, demonstrates only a
sound conditional syntax rule: from `S ⊑ (A ⊓ B)` derive `S ⊑ A` and
`S ⊑ B`, with argument-selection witnesses. It **does not** derive
`S ⊑ Index` from `∃uses.Index`, nor extract one disjunct from `A ⊔ B`.
The rule checks the expression tree, not its scientific source.

The paired API preview renderer is
`curricula-live/api/core/formal_class_models.py`. It generates Unicode,
escaped LaTeX and mechanical text from the typed AST; nothing is attached to a
live concept Overview until the canonical modeling and admission rules exist.

## Future admission decisions

Before expanding beyond synthetic fixtures, settle source provenance, identity
crosswalk, role/property semantics, context/sort checking and necessary versus
sufficient conditions. The current schema deliberately does not allow an
`approved` status, canonical publication, or an untyped bag of metadata.


## Experimental propositional proof language v0

This is deliberately **separate** from description-logic class expressions.
The formula AST uses `atom`, `top`, `bottom`, `not`, `and`, `or`,
`implies`, and `iff`; these denote propositional connectives, not
`subtype_of` or class union/intersection. Variables `P` and `Q`
represent abstract truth-valued atoms, **not** canonical concept identities or
facts imported from the ontology.

A synthetic proof certificate lists bounded, numbered steps. Each step can
reference only earlier steps; there is no `axiom` or `trust_me` shortcut.
The experimental natural-deduction checker currently supports:

- `assume`: open an explicitly tracked hypothesis;
- `and_intro`, `and_elim_left`, `and_elim_right`;
- `imp_elim` (modus ponens) and `imp_intro` (discharge an assumption);
- `or_intro_left`, `or_intro_right`, without unsound selection of a disjunct;
- `iff_elim_left`, `iff_elim_right`, without invented equivalences.

Negation and constants are accepted as **formula syntax**, not as unrestricted
proof rules. First-order quantification, terms, equality, ring axioms,
connection to semantic graph claims, and other proof rules are outside v0.

A worked synthetic proof certificate shows:

```text
h1: P                          [assume]
h2: P ⇒ Q                      [assume]
s1: Q                          [imp_elim h2 h1]
s2: (P ⇒ Q) ⇒ Q                [imp_intro h2 s1; h2 discharged]
s3: P ⇒ ((P ⇒ Q) ⇒ Q)          [imp_intro h1 s2; h1 discharged]
```

The checker returns a trace with exact premise-step IDs and current open
assumptions. A **closed** derivation has none; an **open** derivation is only a
conditional consequence of its hypotheses. For at most eight atom names the
API additionally checks the conclusion against every Boolean valuation.
These verifications establish validity *within the experimental calculus*.
They **do not** establish whether any source-backed claim is scientifically
true or whether its canonical identity is correct.

Reproduction (the paired API proof checker lives in the separate API PR):

```bash
python scripts/validate_formal_proposition.py tests/fixtures/propositional-deduction.synthetic.json
pytest -q tests/test_formal_proposition.py
```

No canonical statements/definitions, database publication, public web
endpoints, or per-concept Markdown records are involved.
