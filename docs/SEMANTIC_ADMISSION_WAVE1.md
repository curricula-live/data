# Semantic admission wave 1 — scope, evidence and inference boundaries

This is an **editorially screened, source-backed** admission batch, not an
independently peer-reviewed scientific ontology or proof of completeness.
It layers on top of the drafted CSO 3.5 and historical V1 source reconciliation.

## Canonical changes

| Canonical object | Stacked source PR | This branch |
|---|---:|---:|
| Concepts | 2,410 | 2,410 |
| Predicates | 19 | **24** |
| Statements | 663 | **764** |
| Definitions | 0 | 0 |
| New statement evidence records | 0 | **101** |
| Published predicate semantic policies | 0 | **5** |

Admitted statements are listed in
`knowledge/statement-admissions.jsonl` and their predicate semantics in
`knowledge/predicate-policies.jsonl`. They are regenerated reproducibly by
`scripts/admit_semantics.py` from two explicit, versioned reviewed allowlists
under `pipeline/semantic-admission/`.

## 87 CSO topic-organization statements

The **Computer Science Ontology v3.5** publisher defines `superTopicOf` as
a research topic being a super-area of another research topic:
https://cso.kmi.open.ac.uk/about

We manually inspected candidate pairs and selected 87 direct edges where
both endpoint identifiers resolve uniquely to existing canonical concept
candidates, the original source triple is in the byte-pinned CSO release,
and the *editorial research-topic interpretation* is not obviously
misleading. These are represented by `research_topic_parent_of`, which is
specifically a CSO-reported organization claim:

- It is **NOT** `subtype_of`, `instance_of`, `prerequisite_of`,
  `implements`, or an unqualified scientific relation.
- It is **NOT** a claim that the named thing is an ontological class
  with a subclass axiom or a learner's required prerequisite.
- It is **NOT** automatically transitive. Longer source paths are
  navigational witnesses, not proof-producing type inferences.
- CSO applies automatically derived research-topic classifications;
  even publisher-attested direct edges are not infallible.
- An admission's local identity match is restricted to that edge;
  it does not authorize global alias, `owl:sameAs` or equivalence merges.

Examples admitted by explicit screen: Artificial Intelligence >
Machine Learning; Graph Theory > Directed Acyclic Graph; Probability >
Conditional Probability; User Interface > Graphical User Interface.

Examples withheld despite source assertions: Authentication >
Authorization, TCP > UDP, IPv6 > IPv4, and Physical Layer > Data Link Layer.
The `directed graph` / `undirected graph` equivalence remains wholly
unadmitted.

## 14 independently cross-checked historical core statements

Specific archived V1 relations survived explicit independent source
cross-checks, without claiming expert peer review or machine proof:

- Stack / Queue operations and LIFO / FIFO order:
  https://www.cs.cornell.edu/courses/cs2110/2026sp/lectures/lec15/
- AND / OR / NOT gates implement Boolean operations:
  https://www.analog.com/en/resources/glossary/logic-gate.html
- Boolean True / False:
  https://docs.python.org/3/library/stdtypes.html#boolean-type-bool
- The two bit values:
  https://csrc.nist.gov/glossary/term/bit

No archived `broaderTopic` edges were automatically admitted. We did not
promote unsupported `relatedEquivalent`, `contributesTo`, `owl:sameAs`,
curriculum placement, algorithm-correctness claims, or any assertion that
lacks an exact source witness.

## Five explicit predicates

- `research_topic_parent_of`: publisher-attested research-area organization.
- `adt_supports_operation`: conventional abstract data type operation.
- `adt_has_discipline`: FIFO or LIFO ordering, scoped to the corresponding ADT.
- `logic_gate_implements_operation`: named Boolean gate and its basic operation.
- `value_of_type`: True/False and binary digit 0/1 under two-valued semantics.

Each predicate has a readable semantics statement in Git and in the
PostgreSQL `knowledge.predicate_semantic_policy` table. The table
enforces **transitive=false, symmetric=false,
safe_for_subtype_inference=false, safe_for_prerequisite_inference=false,
safe_for_formal_proof=false**.

## Atomic PostgreSQL publication

Install BOTH migrations in a disposable environment:

    psql "$DATABASE_URL" -f database/migrations/0001_knowledge_core.sql
    psql "$DATABASE_URL" -f database/migrations/0005_knowledge_statement_admission.sql
    python scripts/validate_v2.py
    python scripts/publish.py apply --confirm-publish PUBLISH
    python scripts/publish.py verify

The publisher now treats the 101 admissions and five policies as part of
the **same canonical transaction**, and verifies them for idempotence and
drift. Missing required DB schema fails closed. The new table constraints
forbid unsupported claims of proof, inference eligibility or independent
expert review.

Executed twice against an isolated local PostgreSQL instance on tower:
2,410 concepts, 24 predicates, 764 statements, **101** evidence records,
**5** predicate policies, zero upgraded inference/proof flags.

**Do not run against production until PRs are reviewed and source identity
proposals are formally admitted.** This feature branch is stacked on the
source import PR and must not be merged or deployed on its own.

## Further admission

**153,862** source relations have not been promoted. They remain searchable
and reviewable in source staging. Additional canonical promotions need
reviewed source/concept identities, a precise predicate meaning, appropriate
evidence, and a test that detects unsupported conversion to stronger logical
relations.
