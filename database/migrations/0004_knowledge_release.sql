-- Install only on a reviewed target. The publisher remains a separate explicit step.
create table if not exists knowledge.publication (
    singleton boolean primary key default true check (singleton),
    git_commit text not null check (git_commit ~ '^[0-9a-f]{40}$'),
    published_at timestamptz not null default now()
);
