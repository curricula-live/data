# Canonical knowledge

This directory contains the published factual knowledge model.

Files:

- `concepts.jsonl` — UUID-backed canonical concepts (`id`, `slug`, `label` only at first);
- `predicates.jsonl` — small controlled relation vocabulary;
- `statements.jsonl` — typed factual statements;
- `definitions.jsonl` — one canonical definition structure per concept, expressed as a set of statement IDs.

## Rules

- Do not add a generic `description` field.
- Do not encode curriculum/provider membership here.
- Do not copy syllabus wording or source documents here.
- Do not add level-specific definitions.
- Prefer explicit relationships over prose or metadata bags.
- Use literals only for genuine values.
- Keep the predicate vocabulary small and add predicates deliberately.

The v2 files intentionally begin empty. The existing production corpus must be reconciled into stable UUID-backed records before it is promoted into this directory.

## Source-attested semantic admissions (draft)

The first admission wave adds `statement-admissions.jsonl` (101 per-statement
witnesses, review tiers and evidence URLs) and `predicate-policies.jsonl`
(5 precisely scoped predicates). Both are atomically published with the
corresponding statements; none is a machine proof, independently expert
approved, a class subtype or a teaching prerequisite. See
[docs/SEMANTIC_ADMISSION_WAVE1.md](../docs/SEMANTIC_ADMISSION_WAVE1.md).
