-- curricula.live knowledge architecture v2
--
-- TARGET MIGRATION ONLY.
-- Do not apply to production until the Git corpus and API are migrated together.

create schema if not exists knowledge;
create schema if not exists curriculum;
create schema if not exists admin;

create table if not exists knowledge.concept (
    id uuid primary key,
    slug text not null unique,
    label text not null,
    constraint concept_slug_format check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    constraint concept_label_not_blank check (btrim(label) <> '')
);

create table if not exists knowledge.predicate (
    slug text primary key,
    label text not null,
    constraint predicate_slug_format check (slug ~ '^[a-z][a-z0-9_]*$'),
    constraint predicate_label_not_blank check (btrim(label) <> '')
);

create table if not exists knowledge.statement (
    id uuid primary key,

    subject_concept_id uuid null,
    subject_statement_id uuid null,

    predicate_slug text not null references knowledge.predicate(slug),

    object_concept_id uuid null,
    object_statement_id uuid null,
    literal_value jsonb null,
    literal_datatype text null,

    constraint statement_subject_exactly_one check (
        num_nonnulls(subject_concept_id, subject_statement_id) = 1
    ),
    constraint statement_object_exactly_one check (
        num_nonnulls(object_concept_id, object_statement_id, literal_value) = 1
    ),
    constraint statement_literal_pair check (
        (literal_value is null and literal_datatype is null)
        or
        (literal_value is not null and literal_datatype is not null and literal_datatype ~ '^[a-z][a-z0-9_]*$')
    ),

    constraint statement_subject_concept_fk
        foreign key (subject_concept_id)
        references knowledge.concept(id)
        deferrable initially deferred,

    constraint statement_object_concept_fk
        foreign key (object_concept_id)
        references knowledge.concept(id)
        deferrable initially deferred
);

alter table knowledge.statement
    add constraint statement_subject_statement_fk
    foreign key (subject_statement_id)
    references knowledge.statement(id)
    deferrable initially deferred;

alter table knowledge.statement
    add constraint statement_object_statement_fk
    foreign key (object_statement_id)
    references knowledge.statement(id)
    deferrable initially deferred;

create index if not exists statement_subject_concept_idx
    on knowledge.statement(subject_concept_id)
    where subject_concept_id is not null;

create index if not exists statement_object_concept_idx
    on knowledge.statement(object_concept_id)
    where object_concept_id is not null;

create index if not exists statement_predicate_idx
    on knowledge.statement(predicate_slug);

-- Exactly one canonical definition structure may exist per concept.
create table if not exists knowledge.definition (
    concept_id uuid primary key
        references knowledge.concept(id)
        on delete cascade
        deferrable initially deferred
);

create table if not exists knowledge.definition_statement (
    concept_id uuid not null
        references knowledge.definition(concept_id)
        on delete cascade
        deferrable initially deferred,
    statement_id uuid not null
        references knowledge.statement(id)
        on delete cascade
        deferrable initially deferred,
    primary key (concept_id, statement_id)
);

comment on schema knowledge is
    'Canonical curriculum-neutral factual knowledge.';

comment on schema curriculum is
    'External curriculum overlays mapping educational structures to canonical knowledge.';

comment on schema admin is
    'Operational administration identity, authorization, audit and review data; not canonical public knowledge.';
