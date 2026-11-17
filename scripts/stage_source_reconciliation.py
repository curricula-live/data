"""Explicit, local-only PostgreSQL staging of unreviewed source assertions.

DO NOT USE ON A PRODUCTION HOST. Only the knowledge_source namespace is
modified, and its database constraints forbid inference_eligible=true.
No canonical identities, predicates, definitions or statements are changed.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import uuid

import psycopg
from psycopg.conninfo import conninfo_to_dict
from reconcile_source_relations import ROOT, OUT, CSO, V1, CSO_ID, V1_ID, records

SOURCE_IDS=(CSO_ID,V1_ID)
EXPECTED_TOPICS=14636+2001
EXPECTED_PREDICATES=14
EXPECTED_ASSERTIONS=151882+2081

def local_database_only(database_url):
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    cfg=conninfo_to_dict(database_url)
    host=cfg.get("host", "localhost")
    if host not in ("127.0.0.1","localhost","::1"):
        raise ValueError("Only disposable local PostgreSQL hosts are authorized for source staging")
    dbname=cfg.get("dbname","")
    if any(k in dbname.casefold() for k in ("production","prod","main")):
        raise ValueError("Database name suggests production; refusing staging")
    return database_url

def manifest():
    return json.loads((OUT/"manifest.json").read_text())

def plan():
    m=manifest()
    return {
        "schema":"knowledge_source",
        "sources":list(SOURCE_IDS),
        "topics":EXPECTED_TOPICS,
        "predicates":EXPECTED_PREDICATES,
        "assertions":EXPECTED_ASSERTIONS,
        "inference_eligible":0,
        "canonical_knowledge_mutations":0,
        "input_verified": (
            m["source_rows"]["historical-v1"]["processed"]==2081 and
            m["source_rows"]["cso"]["processed"]==151882 and
            m["predicate_proposals"]==14 and
            not m["canonical_statement_promotions"]
        ),
    }

def row_streams():
    cso_manifest=json.loads((CSO/"manifest.json").read_text())
    v1_manifest=json.loads((V1/"manifest.json").read_text())
    yield "corpus",iter([
      (CSO_ID,"3.5",cso_manifest["archive_sha256"],"source_only_unreviewed",
       cso_manifest["license"],cso_manifest["attribution"]),
      (V1_ID,"1.0.0",v1_manifest["input_sha256"],"historical_unreviewed",None,
       "curricula-live/ontology archived V1"),
    ])
    mapping={x["source_uri"]:x for x in records(ROOT/"pipeline/historical-v1-identity-proposals.jsonl")}
    candidates={x["source_uri"]:x["canonical_candidate_ids"]
                for x in records(CSO/"canonical-identity-candidates.jsonl")}
    def topic_rows():
        for x in records(CSO/"topics.jsonl"):
            yield (CSO_ID,x["uri"],x["label"],
                   [uuid.UUID(y) for y in candidates.get(x["uri"],[])],
                   "lexical_candidate_unreviewed" if x["uri"] in candidates else "source_only")
        for x in records(V1/"terms.jsonl"):
            state=mapping[x["source_uri"]]
            ids=[uuid.UUID(state["candidate_id"])] if "candidate_id" in state else []
            yield (V1_ID,x["source_uri"],x["label"],ids,
                   state["review_status"])
    yield "topic",topic_rows()
    yield "predicate",(
        (x["source_id"],x["native_predicate"],x["proposed_predicate_slug"],
         x["semantic_family"],False,x["review_status"])
        for x in records(OUT/"predicate-proposals.jsonl")
    )
    def assertions():
        for x in records(OUT/"historical-statement-proposals.jsonl"):
            a=x["subject_candidate_concept_id"]
            b=x["object_candidate_concept_id"]
            yield (x["source_id"],x["source_assertion_uri"],x["subject_source_uri"],
                   x["native_predicate"],x["object_source_uri"],
                   [uuid.UUID(a)] if a else [],[uuid.UUID(b)] if b else [],
                   x["reconciliation_status"],False)
        for x in records(OUT/"cso-statement-proposals.jsonl.gz"):
            yield (x["source_id"],x["source_assertion_uri"],x["subject_source_uri"],
                   x["native_predicate"],x["object_source_uri"],
                   [uuid.UUID(a) for a in x["subject_candidate_concept_ids"]],
                   [uuid.UUID(b) for b in x["object_candidate_concept_ids"]],
                   x["reconciliation_status"],False)
    yield "assertion",assertions()

def counts(cursor):
    return {
      "corpus":cursor.execute(
          "select count(*) from knowledge_source.corpus where id=any(%s)",(list(SOURCE_IDS),)).fetchone()[0],
      **{name:cursor.execute(
          f"select count(*) from knowledge_source.{name} where source_id=any(%s)",
          (list(SOURCE_IDS),)).fetchone()[0]
         for name in ("topic","predicate","assertion")},
    }

def stage(url):
    local_database_only(url)
    if not plan()["input_verified"]:
        raise ValueError("Unverified reconciliation manifest; refusing stage")
    expected={"corpus":2,"topic":EXPECTED_TOPICS,
              "predicate":EXPECTED_PREDICATES,"assertion":EXPECTED_ASSERTIONS}
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            if cur.execute("select to_regnamespace('knowledge_source')").fetchone()[0] is None:
                raise ValueError("Apply reviewed migration 0002 to disposable DB first")
            cur.execute("select pg_advisory_xact_lock(hashtext(%s))",("curricula-source-stage",))
            for table in ("assertion","predicate","topic"):
                cur.execute(f"delete from knowledge_source.{table} where source_id=any(%s)",
                            (list(SOURCE_IDS),))
            cur.execute("delete from knowledge_source.corpus where id=any(%s)",(list(SOURCE_IDS),))
            fields={
                "corpus":"(id,version,archive_sha256,review_status,license,attribution)",
                "topic":"(source_id,source_uri,label,canonical_candidate_ids,identity_review_status)",
                "predicate":"(source_id,native_predicate,proposed_slug,semantic_family,inference_eligible,review_status)",
                "assertion":"(source_id,source_assertion_witness,subject_uri,native_predicate,object_uri,subject_candidate_ids,object_candidate_ids,reconciliation_status,inference_eligible)",
            }
            for table, source_rows in row_streams():
                with cur.copy(f"copy knowledge_source.{table} {fields[table]} from stdin") as copy:
                    for row in source_rows:
                        copy.write_row(row)
            actual=counts(cur)
            if actual!=expected:
                raise ValueError(f"PostgreSQL staging counts mismatch: {actual} != {expected}")
            if cur.execute("select count(*) from knowledge_source.assertion where inference_eligible").fetchone()[0]:
                raise ValueError("Refusing approved inference flag")
            print(json.dumps({"staged":actual,"canonical_knowledge_mutations":0},indent=2))

def verify(url):
    local_database_only(url)
    expected={"corpus":2,"topic":EXPECTED_TOPICS,
              "predicate":EXPECTED_PREDICATES,"assertion":EXPECTED_ASSERTIONS}
    with psycopg.connect(url,options="-c default_transaction_read_only=on") as conn:
        with conn.cursor() as cur:
            actual=counts(cur)
            if actual!=expected:
                raise ValueError(f"Source staging drift: {actual} != {expected}")
            if cur.execute("select count(*) from knowledge_source.assertion where inference_eligible").fetchone()[0]:
                raise ValueError("Inference eligibility violation")
    print(json.dumps({"verified":True,"counts":expected},indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("plan","apply","verify"))
    p.add_argument("--database-url")
    p.add_argument("--confirm-staging",default="")
    a=p.parse_args()
    if a.action=="plan":
        print(json.dumps(plan(),indent=2))
    elif a.action=="apply":
        if a.confirm_staging!="STAGE-UNREVIEWED-SOURCES":
            p.error("Explicit --confirm-staging STAGE-UNREVIEWED-SOURCES required")
        stage(a.database_url or os.getenv("DATABASE_URL"))
    else:
        verify(a.database_url or os.getenv("DATABASE_URL"))
