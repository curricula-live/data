# Scholarly data workflow

This subsystem is additive. It never writes `data/concepts.jsonl`, relations, UUIDs, or a runtime database. Source hierarchy, editorial mappings and definition attestations are distinct records. The current checkout has four seed concepts and no verified UUID export: the reported 554/663/19 baseline cannot be reproduced here.

## Source and licensing register

`source-register.json` records primary-source investigation on 2026-10-15. Null checksums mean **no raw artifact obtained**, not an empty artifact or verified import. Browser-extracted text cannot establish a raw PDF/XLSX checksum. No third-party mirror is presented as an official distribution. No source taxonomy text is committed or published. ACM source access returned 403; the workspace proxy refused connections. CSTA 2017 is historical: the publisher now lists a July 2026 revision. This pipeline's standard-ID validator supports 2017 only; 2026 is a separate audit/import milestone.

## Reproducible ingestion

Obtain the exact official source bytes through authorized access, retain them in an access-controlled location, calculate SHA-256, and create a manifest with id (`acm-ccs`, `cs2023`, `csta`), version, publisher, URL, retrieval date, license, publication scope (`restricted`, `metadata-only`, `public`), distribution (`official`, `third-party`) and sha256. Use filesystem dates only for retrieval, never as inferred publication dates.

```sh
python scripts/scholarly.py import --manifest work/source.json --input work/source.xml --format skos --output work/release.json
python scripts/scholarly.py check work/release.json
python scripts/scholarly.py coverage work/release.json
python scripts/scholarly.py candidates work/release.json --canonical work/verified-uuid-export.jsonl --output work/candidates.json
python scripts/scholarly.py export work/release.json --output work/public.json
```

SKOS support is an adapter, **not a claim that ACM's current distribution has been tested**. It reads explicit broader/narrower relationships and preserves full identifiers, including polyhierarchy. It rejects paper-selection CCSXML. The `curated-json` adapter consumes an array of source-specific records transcribed from an official artifact, with source locators. It is not an automated PDF/XLSX parser: source extraction and transcription review remain outstanding. Record checksum refers to the exact adapter input; if transcribed JSON differs from the original document, register both artifacts and their checksums before making source claims.

Imports are byte-deterministic, fail before replacing output on checksum/validation errors, and record parser version, checksum, format and node count. Re-running with identical input produces identical output. Archive distinct releases by source/version/checksum; never overwrite reviewed versions. `--completeness complete` requires an independently established expected node count. An expected count alone is not scholarly review; compare the official manifest, roots and branches before approval.

CS2023 entities use `knowledge_area`, `knowledge_unit`, `topic`, `learning_outcome`; retain abbreviations, official IDs where present, core classifications and explicit outcome references. When no official topic ID exists, mint an explicitly editorial locator ID and set `official_id: null`. CSTA standard records retain grade_band, concept, subconcept and practices; these facets are not invented scientific parent relationships.

## Review and publication

Mappings require canonical_uuid, canonical_slug, node_id, relation, confidence, status and checksum/locator references. Exact normalized labels generate only `candidate`/`related` suggestions. Ambiguous duplicate labels produce multiple candidates; none are accepted. A reviewer must inspect semantic scope and choose exact/close/related/curriculum_association. Candidate output is a review queue, never a publication artifact. The verified UUID export must be independently checked against the canonical snapshot; seed slugs are insufficient.

Approval requires a named reviewer, date, rationale and references. Source import approval is separate from mapping approval. Public export additionally requires official distribution, explicit public scope and a recorded permission review permitting public commercial redistribution. This is a documented human rights assessment, not an automated legal determination. CSTA NC material remains restricted unless permission covers this use. Metadata-only scope deliberately cannot export taxonomy text; the inventory may link to the official source without copying standards. No CSTA alignment claim is authorized by this software.

Definitions require UUID, slug, text, kind (editorial/quotation/paraphrase/conflicting), responsible author, license, publication scope, citations, review, revision and complete version history. Public definitions additionally need permission evidence. AI-assisted drafts cannot be labelled externally verified. Conflicting definitions stay separate attestations. `definition-pilot.json` is a two-entry **unbound review draft**, not an attestation or import file. UUID binding, exact source bytes/checksums, responsible human authorship, rights review and scholarly review are all pending. Nothing from that file is public data.

The API installer independently reruns the same public contract and accepts only deterministic public-export bytes. `api/core/scholarly_contract.py` is a vendored copy of `scripts/scholarly.py`; update them together and compare hashes. The API deliberately rejects mappings/definitions until the canonical UUID resolver is available in its schema. It preserves the existing slug-only API unchanged.

## Current coverage

Imported source records: 0. Mapped canonical UUIDs: 0. Reviewed mappings: 0. Attested definitions: 0. Published records: 0. Unbound editorial pilot drafts: 2. Source inventory entries: 4 (three source families plus the separate CSTA revision). Synthetic fixtures demonstrate behavior; they never count toward coverage. The 554-concept baseline is user-reported and not verified in this checkout.
