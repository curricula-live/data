# Staging-only v1 → v2 parity verification

The initial 554 concepts, 19 predicate identities, and 663 legacy statement UUIDs
must survive the data model migration. Source-level CI verifies the Git corpus,
but **does not prove PostgreSQL parity**.

After a reviewed staging snapshot has both legacy \`public.*\` tables and
(optionally) the new data-owned \`knowledge.*\` schema:

\`\`\`sh
# A staging-only, SELECT-only database user is required. NEVER production:
STAGING_DATABASE_URL='postgresql://...redacted.../staging' \
  python -m scripts.verify_staging_parity

# When staging v2 publication exists, make full target parity mandatory:
STAGING_DATABASE_URL='postgresql://...redacted.../staging' \
  python -m scripts.verify_staging_parity --require-v2
\`\`\`

- Runs with PostgreSQL \`READ ONLY\` and \`REPEATABLE READ\` transaction settings.
- Compares historical \`public.concept.slug\` against the committed legacy UUID ledger, not current mutable concept slugs.
- Compares \`public.relation\` UUIDs and each original source/predicate/target triple with Git v2 statement UUIDs.
- Allows *additional* post-migration canonical records, without allowing a historic UUID to be silently rekeyed.
- If v2 tables are present, also verifies full canonical readback including all definitions using the existing publisher read model and exact diff.
- Fails closed on counts, missing FKs, ID changes or differing content; prints counts and status only, never database credentials.

This is a staging inspection command, not a migrator. A successful run against
a real staging database is still required before a cutover PR can be approved.
No automatic production migration, publication or rollback is authorized.
