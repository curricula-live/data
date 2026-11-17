import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage_source_reconciliation import local_database_only,plan,row_streams


def test_stage_count_plan_is_not_canonical_knowledge_write():
    p=plan()
    assert p["topics"]==16637
    assert p["predicates"]==14
    assert p["assertions"]==153963
    assert p["inference_eligible"]==0
    assert p["canonical_knowledge_mutations"]==0
    assert p["input_verified"]


def test_rejects_remote_and_production_database():
    for url in (None, "postgresql://postgres@db.example.com:5432/stage",
                "postgresql://admin@localhost:5432/production",
                "postgresql://admin@localhost:5432/main"):
        with pytest.raises(ValueError):
            local_database_only(url)
    assert local_database_only("postgresql://admin@127.0.0.1:5432/review")


def test_explicit_namespace_and_database_constraints():
    sql=(ROOT/"database/migrations/0002_source_reconciliation_staging.sql").read_text()
    assert "create schema if not exists knowledge_source" in sql
    assert "check (not inference_eligible)" in sql
    assert sql.count("check (not inference_eligible)")>=2
    assert "create table if not exists knowledge_source.assertion" in sql
    assert "drop table" not in sql.casefold()
    assert "knowledge.statement" not in sql
    assert "knowledge.concept" not in sql


def test_staging_rows_keep_candidates_and_origins():
    groups={name:it for name,it in row_streams()}
    corpora=list(groups["corpus"])
    assert len(corpora)==2
    predicates=list(groups["predicate"])
    assert len(predicates)==14
    assert all(item[-2] is False for item in predicates)
    topic_iterator=groups["topic"]
    first=next(topic_iterator)
    assert first[0]=="cso@3.5"
    assertion_iterator=groups["assertion"]
    first_statement=next(assertion_iterator)
    assert first_statement[0]=="curricula-historical-v1@1.0.0"
    assert first_statement[-1] is False
