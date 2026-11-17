# Bulk concept coverage — staged CSO 3.5 and archived V1

Status: **DRAFT. Not merged, not published to PostgreSQL, and not approved for inference.**

This feature branch increases useful knowledge in two separate layers.

## Source-scoped coverage (not canonical)

The official CSO v3.5 export is downloaded byte-for-byte, checksum-pinned,
attributed to **Computer Science Ontology (CSO), The Open University**, and
licensed **CC BY 4.0**. Its original N-Triples vocabulary is preserved.
Source download: https://cso.kmi.open.ac.uk/downloads
License: https://cso.kmi.open.ac.uk/faq

The historical curricula.live ontology V1 is a separately labelled, unreviewed
source with a pinned local input digest. It is not imported as authoritative V2.
The source was synthesized in part from educational documents and independently
audited as scientifically insufficient. Its archived relationships must not
be promoted into accepted scientific assertions.

| Layer | Topics | Source URI relations | Predicates |
|---|---:|---:|---:|
| CSO 3.5 | 14,636 labelled | 151,882 | 8 (including label and rdf:type) |
| Historical curricula V1 | 2,001 | 2,081 | 6 |
| Canonical draft | 2,410 | 663 existing statements | 19 existing predicates |

There are 100 additional CSO subject URIs without their own English label;
they remain in the original ZIP and URI relation index, not silently fabricated
as search labels. Counts are based on exact source artifacts, not extrapolation.

## Canonical identity-only proposals

The feature branch adds **1,856 provisional concept identity entries** to
knowledge/concepts.jsonl (554 -> 2,410). They are based on labels from the
historical user-authored conceptual corpus. The full 2,001 decisions are in
pipeline/historical-v1-identity-proposals.jsonl: 142 exact-label existing
candidates, 1,856 new proposals and three collisions withheld.

**Nothing from either source is being asserted as a canonical scientific
relationship**: 663 existing canonical statements remain unchanged, and no
new canonical definition or predicate has been silently added. Existing 19
predicate semantics are unchanged. Newly added UUIDs are scoped candidate
identities, not approved cross-source equivalences or source provenance.
A human review is required before this branch can merge. Neither source
taxonomy nor V1 claims are eligible for the current subtype inference engine.

## Reproduce and explore

Run these commands from the data repo; source archives are neither modified
nor remotely re-downloaded by any of the scripts:

    python scripts/cso35_source_catalog.py import --archive sources/cso-3.5/CSO.3.5.nt.zip
    python scripts/historical_v1_catalog.py --source /path/to/ontology/ontology-consolidated.json
    python scripts/propose_historical_concepts.py
    python scripts/source_coverage_search.py "binary tree"
    python scripts/source_coverage_search.py "TCP"
    python scripts/source_topic_paths.py --source cso --term "computer science" --depth 2
    python scripts/validate_v2.py
    pytest -q

Do not run the proposal script with --apply-to-feature-branch on main or after
the draft has been reviewed without reconciling its decision ledger.

## Required next gates for publishing

1. Review the 1,856 new identity proposals, aliases, homonyms and three
   unresolved collisions. New slugs and UUIDs must not be silently equated
   with source URIs.
2. Publish a database-backed **source-discovery** projection separately from
   canonical concepts. API search should return structured source-only matches
   instead of fabricating 404-proof canonical definitions, and should distinguish
   unknown terms from candidates. Implement suggestions and alias review.
3. Add provenance, semantic scope and review state to any **new canonical
   statement** before promoting CSO or V1 relationships.
4. Define exact inference-safe rules per predicate and enforce that
   unreviewed source relationships never become subtype or pedagogical proof
   premises. Preserve original source edge witnesses.
5. Test ranking, normalization and Romanian/English synonyms using a
   representative held-out CS/ICT term set, not only counts.

No deployment, database publication, schema migration, or inferred fact
approval has been performed by this feature branch.
