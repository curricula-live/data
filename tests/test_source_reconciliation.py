from collections import Counter
from pathlib import Path
import gzip
import hashlib,json,sys,tempfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from reconcile_source_relations import OUT,build,records,predicate_catalog
from review_source_concept import review

def test_every_source_statement_reconciled_and_not_promoted():
    m=json.loads((OUT/"manifest.json").read_text())
    assert m["source_rows"]["cso"]["processed"]==151882
    assert m["source_rows"]["historical-v1"]["processed"]==2081
    assert m["predicate_proposals"]==14
    assert not m["canonical_statement_promotions"]
    assert not m["canonical_relation_type_promotions"]
    assert not m["automatic_subtype_inference_enabled"]
    assert not m["automatic_prerequisite_inference_enabled"]
    assert m["new_concept_coverage"]["total_new_concepts"]==1856
    assert m["new_concept_coverage"]["with_historical_relationship_candidates"]==1854

def test_historical_accepted_premise_gates_and_stable_candidate_uuids():
    c=Counter();witnesses=set();draftids=set()
    for e in records(OUT/"historical-statement-proposals.jsonl"):
        assert not e["accepted_canonical_statement"]
        assert not e["inference_eligible"]
        assert e["source_assertion_uri"] not in witnesses
        witnesses.add(e["source_assertion_uri"])
        c[e["reconciliation_status"]]+=1
        s=e["proposed_statement"]
        if s:
            assert e["reconciliation_status"]=="two_provisional_ids_mapped"
            assert s["predicate"]!="subtype_of"
            assert s["id"] not in draftids
            draftids.add(s["id"])
    assert c=={"two_provisional_ids_mapped":1742,
               "requires_existing_concept_identity_approval":336,
               "blocked_identity_collision":3}
    assert len(draftids)==1742

def test_all_cso_relations_are_source_only():
    counts=Counter()
    for e in records(OUT/"cso-statement-proposals.jsonl.gz"):
        assert e["accepted_canonical_statement"] is False
        assert e["inference_eligible"] is False
        assert e["proposed_statement"] is None
        assert e["source_assertion_uri"].startswith("sha256:")
        counts[e["native_predicate"]]+=1
    expected=json.loads((OUT/"manifest.json").read_text())["source_rows"]["cso"]["predicates"]
    assert dict(counts)==expected

def test_predicate_ontology_remains_semantically_separate():
    types=predicate_catalog()
    assert len(types)==len({x["proposed_predicate_slug"] for x in types})==14
    assert all(not x["canonical_predicate_approved"] and not x["safe_for_subtype_inference"] and
               not x["safe_for_learning_prerequisite_inference"] for x in types)

def test_all_candidate_concepts_have_a_coverage_record():
    records_=list(records(OUT/"per-concept-coverage.jsonl"))
    assert len(records_)==1856
    assert len({x["candidate_concept_id"] for x in records_})==1856
    assert sum(bool(x["incoming_relation_candidates"] or x["outgoing_relation_candidates"])
               for x in records_)==1854
    assert all(not x["canonical_inference_eligible"] for x in records_)

def test_single_concept_review_preserves_uncertainty():
    x=review("binary-tree",3)
    assert x["status"]=="unreviewed_source_candidate"
    assert x["historical"]["count"]>=1
    assert not x["inference_eligible"]
    with pytest.raises(ValueError):
        review("nonexistent-concept")

def test_idempotent_rebuild():
    filenames=["historical-statement-proposals.jsonl","cso-statement-proposals.jsonl.gz",
               "per-concept-coverage.jsonl","predicate-proposals.jsonl","manifest.json"]
    def digest(path):
        contents=path.read_bytes()
        if path.suffix==".gz": contents=gzip.decompress(contents)
        return hashlib.sha256(contents).hexdigest()
    before={x:digest(OUT/x) for x in filenames}
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);build(path)
        after={x:digest(path/x) for x in filenames}
    assert before==after
    m=json.loads((OUT/"manifest.json").read_text())
    assert before["cso-statement-proposals.jsonl.gz"]==m["source_rows"]["cso"]["uncompressed_jsonl_sha256"]
