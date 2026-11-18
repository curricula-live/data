"""Semantic-admission batch regression and source-witness contract."""
import gzip
import json
from collections import Counter
from pathlib import Path
import sys
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from admit_semantics import apply,CSO_PARENT_IRI,CSO,V1,AREA,uri_witness,records,parse_allowlist
from scripts.publish import load_canonical_state,build_plan

def test_admission_wave_counts_and_reproducibility():
    manifest=apply(write=False)
    assert manifest["new_predicates"]==5
    assert manifest["new_statements"]==126
    assert manifest["source_cso_topic_relations"]==112
    assert manifest["externally_corrob_historical_core"]==14
    assert manifest["proof_eligible_statement_count"]==0
    assert json.loads((AREA/"admission-manifest.json").read_text())==manifest
    state=load_canonical_state()
    assert len(state["concepts"])==2412
    assert len(state["predicates"])==24
    assert len(state["statements"])==825
    assert len(state["admissions"])==126
    assert len(state["policies"])==5
    assert len({x["statement_id"] for x in state["admissions"]})==126
    assert len({x["slug"] for x in state["policies"]})==5

def test_every_admitted_cso_source_witness_is_in_original_nt_zip():
    archive=CSO/"CSO.3.5.nt.zip"
    with zipfile.ZipFile(archive) as z:
        original=z.read("CSO.3.5.nt").decode("utf-8")
    corpus_lines=set(original.splitlines())
    statements={x["id"]:x for x in records(ROOT/"knowledge/statements.jsonl")}
    cso_admissions=[x for x in records(ROOT/"knowledge/statement-admissions.jsonl")
                    if x["source_id"]=="cso@3.5"]
    assert len(cso_admissions)==112
    for a in cso_admissions:
        triple=f'<{a["subject_source_uri"]}> <{a["native_predicate"]}> <{a["object_source_uri"]}> .'
        assert triple in corpus_lines
        assert a["source_assertion_witness"]==uri_witness(
            a["subject_source_uri"],CSO_PARENT_IRI,a["object_source_uri"])
        assert a["native_predicate"]==CSO_PARENT_IRI
        assert a["predicate_slug"]=="research_topic_parent_of"
        assert statements[a["statement_id"]]["predicate"]=="research_topic_parent_of"
        assert not a["inference_eligible"] and not a["proof_eligible"]

def test_historical_admissions_corrob_and_explicitly_scoped():
    admissions=[x for x in records(ROOT/"knowledge/statement-admissions.jsonl")
                if x["source_id"]=="curricula-historical-v1@1.0.0"]
    assert len(admissions)==14
    allowed={"hasOperation":5,"hasProperty":2,"implements":3,"valueOfType":4}
    assert dict(Counter(x["native_predicate"] for x in admissions))==allowed
    historical_witnesses={x["assertion_id"] for x in records(V1/"relations.jsonl")}
    for row in admissions:
        assert row["source_assertion_witness"] in historical_witnesses
        assert row["review_level"]=="editorially_corrob_with_external_reference"
        assert row["evidence_urls"] and all(x.startswith("https://") for x in row["evidence_urls"])
        assert row["independent_expert_review"] is False
        assert row["proof_eligible"] is False
    assert all(row["native_predicate"] not in ("broaderTopic","subtopicOf") for row in admissions)

def test_source_hierarchy_inference_and_equivalence_not_promoted():
    admissions=list(records(ROOT/"knowledge/statement-admissions.jsonl"))
    assert not any(x["native_predicate"].endswith("relatedEquivalent") for x in admissions)
    assert not any(x["native_predicate"].endswith("owl#sameAs") for x in admissions)
    assert not any(x["native_predicate"].endswith("contributesTo") for x in admissions)
    assert all(not x["inference_eligible"] for x in admissions)
    assert all(not x["proof_eligible"] for x in admissions)
    assert all(x["identity_review_scope"]=="this_direct_relation_only" for x in admissions)
    policy=list(records(ROOT/"knowledge/predicate-policies.jsonl"))
    assert all(not x["transitive"] and not x["safe_for_subtype_inference"] and
               not x["safe_for_prerequisite_inference"] and not x["safe_for_formal_proof"] for x in policy)

def test_canonical_publisher_detects_missing_or_drifted_admission_provenance():
    state=load_canonical_state()
    same={name:list(rows) for name,rows in state.items()}
    plan=build_plan(state,same)
    assert plan["admissions"]["add"]==0
    assert plan["policies"]["add"]==0
    drift={name:list(rows) for name,rows in state.items()}
    drift["admissions"]=drift["admissions"][1:]
    drift["policies"]=drift["policies"][1:]
    plan=build_plan(state,drift)
    assert plan["admissions"]["add"]==1
    assert plan["policies"]["add"]==1

def test_rejects_unreviewed_changes_to_permitted_source_pair():
    src=AREA/"reviewed-cso-super-topic.tsv"
    rows=[tuple(x.strip().split("|")) for x in src.read_text().splitlines() if x.strip()]
    assert len(rows)==87
    excluded={("authentication","authorization"),("tcp","udp"),
              ("physical layer","data link layer"),("ipv6","ipv4")}
    assert not excluded.intersection(rows)

def test_tampered_admission_flag_cannot_pass_validation(tmp_path,monkeypatch):
    import scripts.validate_v2 as validate
    root=ROOT/"knowledge"
    for name in ("statement-admissions.jsonl","predicate-policies.jsonl"):
        (tmp_path/name).write_bytes((root/name).read_bytes())
    admissions=list(records(tmp_path/"statement-admissions.jsonl"))
    admissions[0]["inference_eligible"]=True
    (tmp_path/"statement-admissions.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in admissions)
    )
    monkeypatch.setattr(validate,"KNOWLEDGE",tmp_path)
    with pytest.raises(SystemExit,match="unsupported scientific verification claim"):
        validate.validate_semantic_admissions(load_canonical_state())

def test_unwitnessed_new_statement_cannot_pass_validation(tmp_path,monkeypatch):
    import scripts.validate_v2 as validate
    root=ROOT/"knowledge"
    for name in ("statement-admissions.jsonl","predicate-policies.jsonl"):
        (tmp_path/name).write_bytes((root/name).read_bytes())
    state=load_canonical_state()
    state["statements"].append({
        "id":"44444444-4444-4444-8444-444444444444",
        "subject":{"kind":"concept","id":state["concepts"][0]["id"]},
        "predicate":"research_topic_parent_of",
        "object":{"kind":"concept","id":state["concepts"][1]["id"]},
    })
    monkeypatch.setattr(validate,"KNOWLEDGE",tmp_path)
    with pytest.raises(SystemExit,match="unattested source-qualified canonical statements"):
        validate.validate_semantic_admissions(state)

def test_predicate_cannot_claim_automatic_class_subsumption(tmp_path,monkeypatch):
    import scripts.validate_v2 as validate
    root=ROOT/"knowledge"
    for name in ("statement-admissions.jsonl","predicate-policies.jsonl"):
        (tmp_path/name).write_bytes((root/name).read_bytes())
    policies=list(records(tmp_path/"predicate-policies.jsonl"))
    policies[0]["safe_for_subtype_inference"]=True
    (tmp_path/"predicate-policies.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in policies)
    )
    monkeypatch.setattr(validate,"KNOWLEDGE",tmp_path)
    with pytest.raises(SystemExit,match="admitted predicate is not proof-safe"):
        validate.validate_semantic_admissions(load_canonical_state())


def test_wave2_is_additive_and_explicitly_held_edges_stay_out():
    old = {tuple(row) for row in parse_allowlist(
        AREA / "reviewed-cso-super-topic.tsv", 87)}
    added = {tuple(row) for row in parse_allowlist(
        AREA / "reviewed-cso-wave2.tsv", 25)}
    held = parse_allowlist(AREA / "held-cso-wave2.tsv", 10)
    assert not old & added
    assert not (old | added) & {tuple(row[:2]) for row in held}
    assert all(len(row) == 3 and row[2].strip() for row in held)
    admitted = {(a["subject_label"], a["object_label"]) for a in records(
        ROOT / "knowledge/statement-admissions.jsonl") if a["source_id"] == "cso@3.5"}
    assert admitted == old | added
    assert ("statistics", "logistic regression") in added
    assert ("statistics", "regression testing") not in admitted


def test_held_relation_cannot_be_added_by_editing_an_allowlist(tmp_path, monkeypatch):
    import admit_semantics as admission
    for name in ("reviewed-cso-super-topic.tsv", "reviewed-cso-wave2.tsv", "held-cso-wave2.tsv", "reviewed-predicate-logical-translations.json"):
        (tmp_path / name).write_bytes((AREA / name).read_bytes())
    path = tmp_path / "reviewed-cso-wave2.tsv"
    rows = path.read_text().splitlines()
    rows[0] = "gpu|cpu"
    path.write_text("\n".join(rows) + "\n")
    monkeypatch.setattr(admission, "AREA", tmp_path)
    with pytest.raises(ValueError, match="Held relationship"):
        admission.apply(write=False)


@pytest.mark.parametrize("tamper", ["endpoint", "witness"])
def test_admission_rejects_identity_or_source_witness_drift(tmp_path, monkeypatch, tamper):
    import scripts.validate_v2 as validate
    for name in ("statement-admissions.jsonl", "predicate-policies.jsonl"):
        (tmp_path / name).write_bytes((ROOT / "knowledge" / name).read_bytes())
    state = load_canonical_state()
    admissions = list(records(tmp_path / "statement-admissions.jsonl"))
    record = next(a for a in admissions if a["source_id"] == "cso@3.5")
    if tamper == "endpoint":
        statement = next(s for s in state["statements"] if s["id"] == record["statement_id"])
        replacement = next(c for c in state["concepts"]
                           if c["label"].casefold() != record["subject_label"].casefold())
        statement["subject"] = {"kind": "concept", "id": replacement["id"]}
        expected = "endpoint differs from reviewed identity"
    else:
        record["object_source_uri"] += "_tampered"
        (tmp_path / "statement-admissions.jsonl").write_text(
            "".join(json.dumps(a, sort_keys=True) + "\n" for a in admissions))
        expected = "source witness differs from original triple"
    monkeypatch.setattr(validate, "KNOWLEDGE", tmp_path)
    with pytest.raises(SystemExit, match=expected):
        validate.validate_semantic_admissions(state)


def test_reviewed_logical_translations_preserve_predicate_scope_and_non_entailments():
    policies = list(records(ROOT / "knowledge/predicate-policies.jsonl"))
    assert len(policies) == 5
    symbols = set()
    for policy in policies:
        logic = policy["logical_translation"]
        assert logic["form"] == "scoped_binary_relation" and logic["arity"] == 2
        assert logic["allowed_conditional_rules"] == ["conjunction_introduction", "existential_introduction"]
        assert not logic["class_subsumption"]
        assert not logic["closed_world_negation"]
        assert not logic["equivalence_from_edge"]
        assert not policy["transitive"] and not policy["safe_for_subtype_inference"]
        symbols.add(logic["symbol"])
    assert len(symbols) == 5


def test_logical_translation_cannot_be_silently_changed(tmp_path, monkeypatch):
    import scripts.validate_v2 as validate
    for name in ("statement-admissions.jsonl", "predicate-policies.jsonl"):
        (tmp_path / name).write_bytes((ROOT / "knowledge" / name).read_bytes())
    policies = list(records(tmp_path / "predicate-policies.jsonl"))
    policies[0]["logical_translation"]["class_subsumption"] = True
    (tmp_path / "predicate-policies.jsonl").write_text(
        "".join(json.dumps(p,sort_keys=True)+"\n" for p in policies))
    monkeypatch.setattr(validate, "KNOWLEDGE", tmp_path)
    with pytest.raises(SystemExit, match="logical translation differs from review"):
        validate.validate_semantic_admissions(load_canonical_state())
