# Logical interpretations of admitted ontology relations

This change maps the five admitted predicate types to explicit scoped binary relation atoms over named knowledge entities. It changes neither the 126 admitted statements nor their inference/proof eligibility flags.

| Native source predicate | Admitted predicate | Logical atom |
| --- | --- | --- |
| CSO superTopicOf | research_topic_parent_of | ResearchTopicParentOf(A, B) in the direct research-topic organizational scope |
| Historical hasOperation | adt_supports_operation | SupportsOperation(A, O) in the abstract interface scope |
| Historical hasProperty (selected FIFO/LIFO claims only) | adt_has_discipline | HasDiscipline(A, D) in the abstract ordering scope |
| Historical implements (selected gate claims only) | logic_gate_implements_operation | ImplementsBooleanOperation(G, O) in two-valued digital logic |
| Historical valueOfType | value_of_type | ValueOfType(V, T) over a named value and type |

These atoms concern the named denotations of the concept records. In particular, an operation supported by an abstract data type is not silently reinterpreted as a universal assertion about all instances of every implementation, and value membership is not class subsumption.

The reviewed contracts live in `pipeline/semantic-admission/reviewed-predicate-logical-translations.json` and are included in each published `knowledge.predicate_semantic_policy` record. Generation and canonical validation require the committed reviewed contracts. Unknown predicates have no admitted logical translation.

## Conditional inference rules

For actual retrieved premises, conjunction introduction may combine two or more scoped atoms. Existential introduction may replace one named endpoint with a bound variable, using that exact endpoint as a witness. These are conditional logical consequences of the recorded assertions; source truth is not certified and no new statements are written to canonical knowledge.

The companion API readout retains each premise's canonical statement UUID and original source witness, computes the conclusion expression, and checks it against the rule before returning it. Scope and relation direction are preserved. Different semantic scopes are not combined into a single relation group.

Examples verified through the real Django API against a disposable PostgreSQL publication:

- Stack ADT supports Stack peek, Stack push and Stack pop: conjunction of three actual canonical statements.
- Queue ADT supports Queue enqueue and Queue dequeue: conjunction of two actual canonical statements.
- Boolean type has recorded values Boolean true and Boolean false: conjunction of incoming value-membership statements, not a subtype claim or an exhaustive enumeration.
- Artificial intelligence's directly recorded subtopics remain source-organizational relations, without transitive subtype promotion.

No absent edge supplies negation; no directional edge supplies an equivalence. OR, NOT and IFF concept assertions need explicit reviewed statements or definition structures that express those meanings. Generic Boolean demonstrations are not part of this path.

Validation: 80 data tests passed, 18 skipped; scoped projection/API tests passed; canonical publication and exact verification passed in isolated PostgreSQL. No hosted database was changed.
