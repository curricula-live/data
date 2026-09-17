# Knowledge architecture v2

## Purpose

The v2 model separates four concerns that were previously easy to blur together:

```text
canonical knowledge
      ↑
      │ mapped from
curriculum overlays

external ingestion inputs ──> candidate reconciliation ──> canonical knowledge

admin identity/audit ──> operational governance of edits and releases
```

Only canonical knowledge and reviewed curriculum mappings are published from Git.

## Knowledge model

The factual model is deliberately small.

### Concept

A reusable unit of knowledge with:

- stable UUID identity;
- unique mutable slug;
- human label.

No generic description field is part of the canonical concept model.

### Predicate

A small controlled vocabulary of relation names such as `instance_of`, `part_of`, `requires`, or `represents`.

Predicates use readable slugs and should be introduced sparingly.

### Statement

A statement has a stable UUID and the shape:

```text
subject ── predicate ──> object
```

A subject may be a concept or another statement. An object may be a concept, another statement, or a literal value.

This is sufficient to represent both ordinary concept relations and statements about statements while remaining normal PostgreSQL.

Example:

```text
statement A:
queue ── instance_of ──> abstract-data-type

statement B:
statement A ── requires ──> fifo
```

The model is RDF/Wikidata-inspired but does not require RDF storage, Wikibase, Wikidata identifiers, or a graph-database engine.

### Definition

A canonical definition is not free text. It is a reviewed set of canonical statement IDs associated with one concept.

There is at most one canonical definition structure per concept.

Educational level does not create alternate definitions. If a curriculum teaches the concept at a particular stage, that fact belongs to `curriculum`. If a classroom product needs a simpler explanation, that adaptation belongs to the presentation/didactic layer.

## Literals

Not every value should become a concept. Numbers, dates, code fragments, representations and similar irreducible values may be statement literals.

The rule is semantic rather than ideological: use relationships when the object is knowledge; use a literal when the object is genuinely a value.

## Curriculum overlay

Curriculum data answers questions such as:

- where is this concept taught?
- under which programme/version/topic?
- what curriculum node maps to which canonical concept?

It must never define concept identity or force provider-specific wording into canonical knowledge.

## Ingestion

Syllabi, textbooks, standards, Wikidata and similar materials are external inputs used to discover candidate concepts and relations.

The canonical pipeline is:

```text
external material
      ↓
extract candidates
      ↓
normalize terminology
      ↓
reconcile against existing UUID-backed concepts
      ↓
human review
      ↓
canonical Git change
```

The external document itself is not copied into the public knowledge model. Import/review tooling may keep private operational traces needed to reproduce editorial work, but those traces are not concept facts.

## Database ownership

The shared domain schema is owned here because both the public API and the future admin application consume it.

Initial schemas:

- `knowledge` — concepts, predicates, statements, definitions;
- `curriculum` — curriculum overlays;
- `admin` — reserved for operational identity/authorization/audit records.

`admin` records are runtime operational data and are not serialized as canonical public knowledge.

## Publishing

```text
feature branch
    ↓
PR to dev
    ↓
validation / review
    ↓
dev
    ↓
release PR
    ↓
main
    ↓
database migration / canonical data publication
    ↓
runtime PostgreSQL
```

The runtime database may be recreated from repository-controlled schema history plus canonical releases. No production host is itself the source of truth.
