# Verification and blockers — 2026-10-15

Status: partial local development implementation; scholarly data milestone incomplete.

## Checks

- `python scripts/sync.py check --format`: passed, unchanged 4-concept/4-relation seed.
- Data `pytest -q`: 22 passed.
- API `pytest -q`: 109 passed, including legacy regression suite; isolated SQLite only.
- Django system check: passed. Migration drift: no changes detected.
- API vendored scholarly contract: byte-identical to Data ingestion contract.
- Web TypeScript: passed. ESLint: no errors, three existing search-loading image warnings.
- Web production build: passed, including `/atlas`. Next.js detached TypeScript CLI returned empty output in this runtime; compiler API mode retains type checking and builds successfully.
- PostgreSQL migration execution: blocked; Docker daemon socket denied access.
- Live server/UI smoke: blocked; runtime refuses local listening sockets with EPERM. No visual browser verification claimed.
- Remote dev fetch: failed for all repositories, proxy connection refused. Local dev branches were created from supplied clean work checkouts; latest remote dev ancestry is unverified. No push performed.

## Coverage

Imported authoritative source records: **0**. Canonical UUID concepts with mappings: **0**. Reviewed mappings: **0**. Attested definitions: **0**. Published scholarly records: **0**. Unbound AI-assisted editorial drafts: **2**. Inventory: **4** entries across three source families, separating CSTA versions. Synthetic fixtures do not count as scholarly data.

The 554 concepts / 663 statements / 19 predicates baseline is user-reported, not available in this checkout. Data has a four-concept seed and API models are slug-only. No UUIDs or canonical graph records were changed.

## Remaining work and blockers

1. Official ACM taxonomy bytes, confirmed download URL and redistribution rights: browser returned 403 for ACM landing/tool. No third-party mirror substituted.
2. Raw CS2023/CSTA artifacts and checksums: browser can inspect official documents but workspace proxy cannot download exact bytes. Null checksums remain explicit in the register.
3. CS2023 full-report permission and controlled topic/outcome extraction. The final-report cover identifies version 2024-04-28. No bulk PDF/XLSX parser is claimed; curated JSON ingestion requires transcription/source review.
4. CSTA 2017 NC/SA restrictions, commercial permission and alignment review. Publisher lists July 2026 revision; 2026 needs its own audit and parser. No standard text or alignment claim published.
5. Verified UUID snapshot and API resolver: needed to generate real mapping candidates and bind definitions. Installer fails closed for mappings/definitions in this checkout.
6. Responsible human authorship, scholarly mapping/definition review and publication rights: all unresolved. No AI-generated text marked externally verified.
7. PostgreSQL and live browser integration tests; remote dev reconciliation and publication.
8. Outstanding production security gates were not assessed or certified by this work.

No production DB mutation or deployment was performed. The requested projectless output path does not exist in this managed executor and its root filesystem is read-only; committed repository documentation is the review record.

## Local development commits

Data: see the commit containing this file. API: `f5c449c`. Web: `c69a134`.
