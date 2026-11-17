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
- `iff_elim_left`, `iff_elim_right`, and `iff_intro`, which requires
  independently justified implications in both directions.

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


## Experimental canonical-statement → propositional-atom bridge

This stage is **not** a scientific facts import. It connects an abstract
propositional atom to an *existing recorded* canonical statement UUID, with
full-file SHA-256 snapshot fingerprints to detect changes in either concept
identities or recorded assertions.

`formal-statement-bindings.v0.schema.json` includes:

- `scope = provisional_canonical_graph`;
- `provenance.status = synthetic_fixture` and `source_scientific_review = not_established`;
- checksums of exact `concepts.jsonl` and `statements.jsonl` bytes;
- a bounded list of `atom` → `statement_id` bindings.

There is **no concept-specific source adapter**. A single reader verifies
the source snapshot, resolves original subject/predicate/object identities,
then projects any selected recorded concept-to-concept claim into a named atom.
The paired API checker independently validates the mapping against supplied
source JSONL bytes and validates each proof step. A complex assumed formula
cannot masquerade as a single recorded statement in this prototype.

For a small example, both selected recorded UUIDs already exist in the
canonical graph:

```text
P := recorded UUID 048adf33-...    (Array subtype_of Collection)
Q := recorded UUID 15ead31d-...    (Collection subtype_of Data)
h1: P                              [recorded assertion used as assumption]
h2: Q                              [recorded assertion used as assumption]
s1: P ∧ Q                          [and_intro h1 h2]
```

The resulting entailment is **conditional** (`P,Q ⊢ P∧Q`). No new
concept-to-concept statement is created. In particular,
`Array subtype_of Data` is **not** obtained merely by propositional
conjunction; it requires a *separately specified* and scoped
`subtype_of` transitivity rule whose semantic applicability has been
reviewed. The older teacher-graph API has a provisional subtype inference;
this new prototype is not an alternative publisher for it.

To reproduce the review with canonical bytes in this checkout:

```bash
python scripts/validate_statement_bindings.py tests/fixtures/recorded-array-bindings.synthetic.json
python scripts/validate_formal_proposition.py tests/fixtures/recorded-array-conjunction.synthetic.json
```

In a checkout of the paired API formal PR (paths may vary):

```bash
python -m core.formal_recorded_statement_bridge \
  --concepts ../data/knowledge/concepts.jsonl \
  --statements ../data/knowledge/statements.jsonl \
  --bindings tests/fixtures/recorded-array-bindings.synthetic.json \
  --proof tests/fixtures/recorded-array-conjunction.synthetic.json
```

The runtime of this helper is deliberately **read-only and local**: no API
route, no automatic canonical knowledge writer, no source-rights approval,
and no database edits. In the future the canonical adapter may consume a
stable DB snapshot rather than Git JSONL, but it must retain the UUID and
source-version guarantees.


## Hypothetical scoped subtype inference v0

The following is a **research-only** mechanism for making an actual, inspectable
graph deduction, distinct from a purely propositional conjunction of recorded
claims.

`schema/knowledge/formal-scoped-subtype-proof.v0.schema.json` stores a
bounded, ordered proof of a `subtype_of` relationship. A source premise
`recorded_subtype` points to an **existing canonical statement UUID**.
A derived step applies **only** `subtype_transitivity`:

```text
subtype_of(A,B) [scope S]   subtype_of(B,C) [scope S]
-----------------------------------------------------  subtype_transitivity
              subtype_of(A,C) [scope S]
```

A proof is checked against SHA-256-pinned canonical `concepts.jsonl` and
`statements.jsonl` bytes. The checker verifies the exact source predicate,
direction, shared intermediate concept, declared scope, ordered premise UUID
chain and claimed goal. It explicitly rejects `uses`, inverted relations,
unknown/missing source IDs, future-referenced steps and mismatched contexts.

**Important scope limitation:** canonical legacy statements do not yet carry
reviewed semantic scopes. For now `scope = hypothetical_...` is an
**external assumption included in the certificate**, not a property certified
by the graph. `scope_origin = assumed_not_in_source` is mandatory. Thus the
deduction is *procedurally valid under a hypothetical common subtype meaning*,
but its science is not established and it must not create a canonical fact.

A sample certificate is checked by:

```bash
python scripts/validate_scoped_subtype_proof.py tests/fixtures/scoped-array-subtype.synthetic.json
pytest -q tests/test_scoped_subtype_proof.py
```

On the paired API branch, **generic discovery** constructs the certificate
from the recorded graph, so there is no per-concept adapter or maintained
Markdown page:

```bash
python -m core.formal_subtype_discovery \
  --concepts ../data/knowledge/concepts.jsonl \
  --statements ../data/knowledge/statements.jsonl \
  --subject array --target data

python -m core.formal_subtype_discovery \
  --concepts ../data/knowledge/concepts.jsonl \
  --statements ../data/knowledge/statements.jsonl \
  --subject integer --target real-number
```

Both examples yield exact UUID-backed, **conditional** transitivity proofs.
The integer-to-real-number chain is a useful reminder that this apparent
mathematical inclusion cannot be promoted as a programming-language type
relation without a reviewed model and context.

The engine does not yet claim to perform general classification, certify
source documents, derive unbounded closure, publish inference outputs, or
integrate this contract with the teacher-facing concept pages. Before
publication, context and predicate semantics need explicit authoritative
review and typed source evidence.


## Typed role signatures for ∃ and ∀ (v0)

A **predicate name** in the recorded concept graph does *not* automatically
carry an individual-level description-logic role interpretation. For example,
`Array uses Index` is a relation between **concept identities** and cannot by
itself establish `Array ⊑ ∃uses.Index` (a claim about instances), much less
`Array ⊑ ∀uses.Index`.

The research contract `schema/knowledge/formal-role-signatures.v0.schema.json`
requires a **separate, scoped, synthetic** declaration:

- An existing canonical `property_slug` whose *identity* is checked against
  the exact SHA-256-pinned `predicates.jsonl` registry.
- `role_sort = object_role` for binary individual-to-individual relations,
  or `data_role` for literal-valued properties. The type checker rejects
  `∃R.C`/`∀R.C` when `R` is a `data_role`; a separate typed datatype
  expression would be necessary.
- Optional `domain_concept_id` and `range_concept_id` are UUIDs or null.
  **If present, they are hypothetical declarations**, not discovered source
  facts or independently proven OWL range/domain axioms.
- `scope = synthetic_...`, provenance
  `role_semantics_origin = assumed_not_in_source`, and `may_publish = false`.

The checker `scripts/validate_formal_roles.py` validates typed role use
against a class-expression AST, without inventing quantifier evidence.
The matching API helper `core/formal_quantified_models.py` independently
checks the signature and outputs typed, escaped Unicode/LaTeX renderings
without granting source verification.

```bash
python scripts/validate_formal_roles.py \
  tests/fixtures/role-signatures.synthetic.json \
  --model tests/fixtures/formal-array.synthetic.json
pytest -q tests/test_formal_roles.py
```

The hypothetical model can render `Array ⊑ (Data Structure ⊓ ∃uses.Index)`
or, with an explicitly different AST, a universal `∀uses.Index` term.
**Neither is admitted as a scientific definition of Array**.

## Equivalence needs two distinct directions

In **propositional** natural deduction, `iff_intro` is now an explicit,
assumption-tracking rule:

```text
h1 : P ⇒ Q                         [assume]
h2 : Q ⇒ P                         [assume]
s1 : P ⇔ Q                         [iff_intro h1 h2]
Open assumptions: h1, h2
```

This produces a **conditional** biconditional, not a theorem, until its two
hypotheses are discharged or justified. The API rule checker independently
tests both implication directions and final truth-table entailment.

A **different** rule applies to description-logic *class equivalence*.
Within **one shared interpretation**, two checked subsumption proofs,
`A ⊑ B` and `B ⊑ A`, conditionally yield `A ≡ B`.
`core/formal_mutual_subsumption.py` checks both full proof certificates
against identical source snapshot fingerprints, their original premise UUIDs,
the **reverse** subject/object identities and matching hypothetical scope.
The module has no source-backed scoped equivalences to publish and the
tests therefore use an entirely synthetic four-class graph.

These are **not interchangeable** symbols: `⇔` links propositions,
`≡` identifies equivalent classes, `⊑` represents class subsumption,
and `⊆` is ordinary set inclusion where its operands really are sets.
A single `subtype_of` edge never warrants either sort of equivalence.

```bash
python scripts/validate_formal_proposition.py \
  tests/fixtures/propositional-biconditional.synthetic.json
pytest -q tests/test_formal_biconditional_schema.py
```

There is still **no new public page formula** for `⇔`, `≡`, `∃` or
`∀` unless the canonical semantic property and its bidirectional evidence
are properly admitted. Client notation support is not a scientific source.
