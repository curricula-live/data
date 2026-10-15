# Ingestion and reconciliation pipeline

External syllabi, standards, textbooks, Wikidata and similar materials are inputs to editorial processing. They are not canonical knowledge stores.

The reproducible workflow is:

```text
external input
    ↓
extract candidate concepts / relations
    ↓
normalize terminology
    ↓
reconcile against canonical UUID-backed knowledge
    ↓
human review
    ↓
Git change
```

## Candidate rules

- extraction output is provisional;
- an extracted term never becomes a new concept merely because a syllabus names it;
- candidate matching should detect aliases, different granularity, and provider-specific wording;
- AI/embedding similarity may suggest matches but must not silently decide canonical identity;
- batch reconciliation should be subject-family-oriented (for example computing across multiple providers) rather than provider-by-provider, reducing ontology bias toward the first syllabus processed.

## Source handling

Do not copy external curriculum documents into the canonical repository or runtime knowledge model.

Private/editorial tooling may retain the minimum operational information necessary to reproduce an import or review decision, but that information is not part of the public factual ontology and must not imply affiliation with any provider.
