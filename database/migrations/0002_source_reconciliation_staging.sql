-- RECONCILIATION REVIEW STAGING ONLY.
-- No migrations or writes to knowledge.*, curriculum.*, admin.*.
-- No source assertion becomes a reviewed scientific canonical statement.
create schema if not exists knowledge_source;

create table if not exists knowledge_source.corpus (
    id text primary key,
    version text not null,
    archive_sha256 char(64) not null check (archive_sha256 ~ '^[0-9a-f]{64}$'),
    review_status text not null,
    license text,
    attribution text
);

create table if not exists knowledge_source.topic (
    source_id text not null references knowledge_source.corpus(id),
    source_uri text not null,
    label text not null,
    canonical_candidate_ids uuid[] not null default array[]::uuid[],
    identity_review_status text not null default 'unreviewed',
    primary key (source_id, source_uri)
);

create index if not exists source_topic_label_search_idx
    on knowledge_source.topic (lower(label) text_pattern_ops);

create table if not exists knowledge_source.predicate (
    source_id text not null references knowledge_source.corpus(id),
    native_predicate text not null,
    proposed_slug text not null,
    semantic_family text not null,
    inference_eligible boolean not null default false check (not inference_eligible),
    review_status text not null default 'unreviewed',
    primary key (source_id, native_predicate)
);

create table if not exists knowledge_source.assertion (
    source_id text not null,
    source_assertion_witness text not null,
    subject_uri text not null,
    native_predicate text not null,
    object_uri text not null,
    subject_candidate_ids uuid[] not null default array[]::uuid[],
    object_candidate_ids uuid[] not null default array[]::uuid[],
    reconciliation_status text not null,
    inference_eligible boolean not null default false check (not inference_eligible),
    primary key (source_id, source_assertion_witness),
    foreign key (source_id, native_predicate)
        references knowledge_source.predicate(source_id, native_predicate)
);
create index if not exists source_assertion_subject_lookup_idx
    on knowledge_source.assertion (source_id, subject_uri);
create index if not exists source_assertion_object_lookup_idx
    on knowledge_source.assertion (source_id, object_uri);
create index if not exists source_assertion_subject_candidates_idx
    on knowledge_source.assertion using gin (subject_candidate_ids);
create index if not exists source_assertion_object_candidates_idx
    on knowledge_source.assertion using gin (object_candidate_ids);

comment on schema knowledge_source is
    'Isolated source assertions, source-native predicates and candidate identity mappings. No approved canonical or inferred facts.';
