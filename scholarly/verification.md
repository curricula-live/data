# Verification and blockers — 2026-10-15 continuation

Status: existing commits recovered and published; canonical PostgreSQL runtime running; **populated ACM CCS Atlas definition of done is NOT met**. No additional ingestion infrastructure was added in this continuation.

## Remote recovery

All original commits are preserved in the published history. Merges preserved current remote Data/API work; no force pushes.

| Repository | Original scholarly commit | Verified remote dev after recovery |
|---|---|---|
| Data | 838778c3718f68f46a8befb599fef7df3c4d4e8b | df5b7474e6c6c55aa81b077570de5935544d82ee |
| API | f5c449c3b0e453e9ba54c5d4de724b4c18ba7e63 | 8e8be7d8645e96771c285e1bab7735d3b4bb992f |
| Web | c69a134e219bfa8f6e065c5acc12ab3ce1e192e0 | c69a134e219bfa8f6e065c5acc12ab3ce1e192e0 |

Remote SHAs were checked with `git ls-remote`. This verification update is a subsequent Data documentation commit; its SHA is reported in chat after publication.

## Actual corpus and runtime

Recovered Data `knowledge/concepts.jsonl`: **554 concepts**, SHA-256 `307ca96200e587408cdb2a4a4e01e8ce90d08a0224873cbd68a27cc958d70285`.
Recovered `knowledge/statements.jsonl`: **663 statements**, SHA-256 `4b13ae0ac0eefa2d6d258e7ea94471d88bcab94290802d4f0be0f875cfdeee2b`.
Predicates: **19**. Canonical definitions: **0**.
Existing legacy identity verification passed for all 554 concept UUIDs and 663 statement UUIDs. These committed identities were copied, never regenerated. Canonical files have no diff against the recovered remote corpus.

Dedicated local container: `curricula-scholarly-dev`, PostgreSQL 17; loopback port 54339; database `scholarly_dev`. Data-owned 0001 schema and existing Django migrations applied successfully. Existing publisher apply and read-only verify reported exact match with zero additions/updates/removals after apply. No public release marker was stamped. Production was not contacted or changed.

Running local API: `http://127.0.0.1:8009/`. Running local Atlas: `http://127.0.0.1:3011/atlas`. Both are loopback-only, with production/public-v2/owner features disabled. These URLs are internal to this executor, not externally published sites.

## Test results

- Data v2 validator: 554 concepts, 19 predicates, 663 statements, zero definitions.
- Data suite without PostgreSQL: 48 passed, 18 skipped.
- Data suite with a separate disposable PostgreSQL contract-test database: **66 passed**.
- API default suite: **222 passed, 19 skipped**.
- API PostgreSQL Atlas integration plus scholarly installer tests in a separate Django test DB: **4 passed**.
- Web typecheck, lint and production build: passed; three existing search-loading image warnings.
- Real headless Chromium: `/atlas` HTTP 200, Scholarly Atlas heading visible, accurate **No reviewed source taxonomy is published yet** empty state. No synthetic release was installed to make this look populated.
- Real Chromium request context: canonical preview collection returned 100 real records; Atlas UUID preview returned **10 concepts and 4 relationships**, all returned UUIDs matched the committed canonical file.
- This is NOT a complete Data → PostgreSQL → ACM API → Atlas test: no official ACM records are available to test that path.

## ACM and mapping coverage

Official ACM bytes obtained: **0**. Imported ACM concepts/edges: **0**. ACM mapping pilot: **0**. Reviewed mappings: **0**. Published taxonomy records: **0**. Existing unbound definition drafts remain unreviewed and are not counted as attestations.

## Genuine remaining blockers

1. **ACM network access**: restricted environment policy permits package/GitHub hosts but does not allow `www.acm.org` or `dl.acm.org`. Elevated HTTP request returned proxy CONNECT 403 before reaching ACM. Environment remains revision 4 with no custom allowed hosts. A request to add those hosts is pending. The official distribution candidate `https://dl.acm.org/pb-assets/dl_ccs/acm_ccs2012-1626988337597.xml` was located via an external pointer; browser fetch also returned 403. Its contents, checksum and completeness have NOT been verified, and no mirror has been substituted.
2. **ACM permission evidence**: rights for the required development ingestion/display and any public redistribution remain unconfirmed. No source content will be imported or displayed without the applicable permission. Network access alone is not publication permission.
3. **Dependent work after source retrieval/permission**: validate actual RDF structure and completeness, wire the recovered UUID resolver into the existing scholarly installer (which still conservatively rejects mappings/definitions), import actual records, create a small explicitly unreviewed pilot in a development-only projection, and verify real browser hierarchy navigation/provenance. No uncertain equivalence will be self-approved.

CS2023 and CSTA remain subsequent deliverables. No production deployment, public taxonomy release, regenerated canonical IDs, or scholarly approval occurred.
