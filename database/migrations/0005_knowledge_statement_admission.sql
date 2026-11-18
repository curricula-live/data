-- Semantic admissions are separate from unreviewed source staging.
-- Only editorially admitted direct statements may have a record here.
-- The table cannot grant logical-proof, subtype or prerequisite status.
create table if not exists knowledge.statement_admission (
    statement_id uuid primary key references knowledge.statement(id)
        on delete cascade deferrable initially deferred,
    source_id text not null,
    source_assertion_witness text not null,
    native_predicate text not null,
    review_level text not null check (review_level in (
        'editorially_screened_source_attested',
        'editorially_corrob_with_external_reference'
    )),
    evidence_urls jsonb not null check (jsonb_typeof(evidence_urls) = 'array'),
    inference_eligible boolean not null default false check (not inference_eligible),
    proof_eligible boolean not null default false check (not proof_eligible),
    independent_expert_review boolean not null default false check (not independent_expert_review),
    review_record jsonb not null check (jsonb_typeof(review_record) = 'object')
);
create index if not exists statement_admission_source_idx
    on knowledge.statement_admission (source_id, source_assertion_witness);
comment on table knowledge.statement_admission is
    'Statement-level source and editorial evidence. Not formal proofs, expert peer review, inferred class subtypes, or educational prerequisites.';

-- Predicate semantics are published and constrained independently from labels.
create table if not exists knowledge.predicate_semantic_policy (
    predicate_slug text primary key references knowledge.predicate(slug)
        on delete cascade deferrable initially deferred,
    semantic_scope text not null,
    semantics text not null,
    source_tier text not null,
    transitive boolean not null default false check (not transitive),
    symmetric_relation boolean not null default false check (not symmetric_relation),
    safe_for_subtype_inference boolean not null default false check (not safe_for_subtype_inference),
    safe_for_prerequisite_inference boolean not null default false check (not safe_for_prerequisite_inference),
    safe_for_formal_proof boolean not null default false check (not safe_for_formal_proof),
    policy_record jsonb not null check (jsonb_typeof(policy_record) = 'object')
);
comment on table knowledge.predicate_semantic_policy is
    'Explicit scoped meanings for new source-admitted predicates. No automatic subsumption, prerequisite, symmetry or transitivity.';
