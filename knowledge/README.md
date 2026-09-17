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
