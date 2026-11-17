"""Explicitly selected source-semantic admissions, with per-claim evidence.

This script only admits direct CSO 3.5 topic-hierarchy claims and independently
corroborated historical core ADT/Boolean statements. Editorial source review
does NOT mean independently expert-verified science or a logical proof.

It never admits owl:sameAs, relatedEquivalent, contributesTo, original V1
broaderTopic, class-subtype claims or pedagogical prerequisites.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

from reconcile_source_relations import (
    ROOT, CSO, V1, OUT, V1_ID, CSO_ID, records, uri_witness,
)

AREA = ROOT / "pipeline/semantic-admission"
CSO_PARENT_IRI = "http://cso.kmi.open.ac.uk/schema/cso#superTopicOf"
CSO_DOC = "https://cso.kmi.open.ac.uk/about"
CSO_DOWNLOAD = "https://cso.kmi.open.ac.uk/downloads"
NATIVE_TO_CANON = {
    "implements": "logic_gate_implements_operation",
    "hasOperation": "adt_supports_operation",
    "hasProperty": "adt_has_discipline",
    "valueOfType": "value_of_type",
}
PREDICATE_POLICIES = [
    {
        "slug": "research_topic_parent_of",
        "label": "Research Topic Parent Of",
        "semantics": "Publisher CSO 3.5 directly classifies the object research topic as a narrower research area of the subject topic, without establishing class membership or ontology subsumption.",
        "semantic_scope": "research_topic_direct_organizational_hierarchy",
    },
    {
        "slug": "adt_supports_operation",
        "label": "ADT Supports Operation",
        "semantics": "The subject abstract data type includes the named object as an operation in its conventional interface; implementation complexity and semantics are not inferred.",
        "semantic_scope": "abstract_data_type_interface",
    },
    {
        "slug": "adt_has_discipline",
        "label": "ADT Has Discipline",
        "semantics": "The subject abstract data type follows the ordering discipline named by its object in conventional stack/queue semantics.",
        "semantic_scope": "abstract_data_type_ordering",
    },
    {
        "slug": "logic_gate_implements_operation",
        "label": "Logic Gate Implements Operation",
        "semantics": "The named Boolean logic gate implements the named Boolean operation for the standard two-valued digital-logic interpretation.",
        "semantic_scope": "binary_boolean_digital_logic",
    },
    {
        "slug": "value_of_type",
        "label": "Value Of Type",
        "semantics": "The subject is a conventional named value of the type represented by the object in the stated Boolean/bit domain.",
        "semantic_scope": "two_valued_boolean_or_binary_digit",
    },
]

def stable_uuid(key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "curricula.live:semantic-admission:2026-11:" + key))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_allowlist(path, count):
    raw = [line.strip().split("|") for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]
    if len(raw) != count or len(set(tuple(row) for row in raw)) != count:
        raise ValueError("Unexpected curated allowlist shape, length or duplicates: " + str(path))
    return raw

def build(existing_concepts, existing_statements):
    concepts = {row["id"]: row for row in existing_concepts}
    if len(concepts) != len(existing_concepts):
        raise ValueError("Nonunique canonical concept identities")
    original = {row["id"]: row for row in existing_statements}
    existing_p = {row["slug"]: row for row in records(ROOT / "knowledge/predicates.jsonl")}
    for policy in PREDICATE_POLICIES:
        if policy["slug"] in existing_p and existing_p[policy["slug"]]["label"] != policy["label"]:
            raise ValueError("Admission predicate definition changed without review.")
    cso_topics = {t["uri"]: t["label"] for t in records(CSO / "topics.jsonl")}
    wave1_pairs = parse_allowlist(AREA / "reviewed-cso-super-topic.tsv", 87)
    wave2_pairs = parse_allowlist(AREA / "reviewed-cso-wave2.tsv", 25)
    pairs = wave1_pairs + wave2_pairs
    if len({tuple(row) for row in pairs}) != len(pairs):
        raise ValueError("Admission waves contain duplicate reviewed pairs")
    held_rows = parse_allowlist(AREA / "held-cso-wave2.tsv", 10)
    if any(len(row) != 3 or not row[2].strip() for row in held_rows):
        raise ValueError("Held relationships require a specific review reason")
    if {tuple(row[:2]) for row in held_rows} & {tuple(row) for row in pairs}:
        raise ValueError("Held relationship cannot enter the admitted allowlist")
    accepted_pairs = {tuple(row) for row in pairs}
    matches = defaultdict(list)
    for row in records(OUT / "cso-statement-proposals.jsonl.gz"):
        if row["native_predicate"] != CSO_PARENT_IRI:
            continue
        src = cso_topics.get(row["subject_source_uri"])
        dst = cso_topics.get(row["object_source_uri"])
        if (src, dst) in accepted_pairs:
            matches[(src, dst)].append(row)
    if set(matches) != accepted_pairs or any(len(group) != 1 for group in matches.values()):
        raise ValueError("CSO curated source witnesses no longer match the pinned release one-to-one")
    stmt, reviews = [], []
    for subject_label, object_label in sorted(accepted_pairs):
        row = matches[(subject_label, object_label)][0]
        ss = row["subject_candidate_concept_ids"]
        oo = row["object_candidate_concept_ids"]
        if len(ss) != 1 or len(oo) != 1 or ss[0] == oo[0]:
            raise ValueError("CSO identity candidate is ambiguous or reflexive")
        if ss[0] not in concepts or oo[0] not in concepts:
            raise ValueError("CSO candidate lacks stable UUID in canonical concept table")
        if concepts[ss[0]]["label"].casefold() != subject_label or concepts[oo[0]]["label"].casefold() != object_label:
            raise ValueError("CSO labels do not match the proposed UUID's canonical label")
        evidence = uri_witness(row["subject_source_uri"], CSO_PARENT_IRI, row["object_source_uri"])
        if evidence != row["source_assertion_uri"]:
            raise ValueError("CSO source hash mismatch")
        sid = stable_uuid("CSO:" + evidence)
        stmt.append({
            "id": sid, "subject": {"kind": "concept", "id": ss[0]},
            "predicate": "research_topic_parent_of",
            "object": {"kind": "concept", "id": oo[0]},
        })
        reviews.append({
            "statement_id": sid,
            "source_id": CSO_ID,
            "source_assertion_witness": evidence,
            "native_predicate": CSO_PARENT_IRI,
            "subject_source_uri": row["subject_source_uri"],
            "object_source_uri": row["object_source_uri"],
            "subject_label": subject_label, "object_label": object_label,
            "predicate_slug": "research_topic_parent_of",
            "decision": "admit_direct_source_report_as_topic_relation",
            "review_method": "explicit_editorial_allowlist_with_exact_source_witness",
            "review_level": "editorially_screened_source_attested",
            "independent_expert_review": False,
            "identity_review_scope": "this_direct_relation_only",
            "inference_eligible": False,
            "proof_eligible": False,
            "source_archive_sha256": json.loads((CSO / "manifest.json").read_text())["archive_sha256"],
            "evidence_urls": [CSO_DOC, CSO_DOWNLOAD],
            "scope_note": "CSO explicitly reports this research-topic parent relation. Neither class-subtype nor pedagogical prerequisite nor transitive logical entailment is asserted.",
        })
    historical_pairs = parse_allowlist(AREA / "reviewed-historical-core.tsv", 14)
    hist_terms = {row["source_uri"]: row["label"] for row in records(V1 / "terms.jsonl")}
    historical_index = defaultdict(list)
    for row in records(OUT / "historical-statement-proposals.jsonl"):
        key = (
            row["native_predicate"],
            hist_terms[row["subject_source_uri"]],
            hist_terms[row["object_source_uri"]],
        )
        historical_index[key].append(row)
    for pred, subject_label, object_label, ref in historical_pairs:
        candidates = historical_index.get((pred, subject_label, object_label), [])
        if len(candidates) != 1 or pred not in NATIVE_TO_CANON:
            raise ValueError("Historically reviewed source relation is missing, duplicated or disallowed")
        if not ref.startswith("https://"):
            raise ValueError("Requires external corroboration URL")
        row = candidates[0]
        proposed = row["proposed_statement"]
        if row["reconciliation_status"] != "two_provisional_ids_mapped" or proposed is None:
            raise ValueError("Historically reviewed relation is not unambiguously mapped to two new identities")
        sc = row["subject_candidate_concept_id"]
        oc = row["object_candidate_concept_id"]
        if concepts[sc]["label"] != subject_label or concepts[oc]["label"] != object_label:
            raise ValueError("Historical concept identity mismatched reviewed labels")
        sid = stable_uuid("HIST:" + row["source_assertion_uri"])
        pred_canonical = NATIVE_TO_CANON[pred]
        stmt.append({
            "id": sid, "subject": {"kind": "concept", "id": sc},
            "predicate": pred_canonical,
            "object": {"kind": "concept", "id": oc},
        })
        reviews.append({
            "statement_id": sid,
            "source_id": V1_ID,
            "source_assertion_witness": row["source_assertion_uri"],
            "native_predicate": pred,
            "subject_source_uri": row["subject_source_uri"],
            "object_source_uri": row["object_source_uri"],
            "subject_label": subject_label, "object_label": object_label,
            "predicate_slug": pred_canonical,
            "decision": "admit_cross_checked_core_fact",
            "review_method": "explicit_editorial_fact_review_with_external_references",
            "review_level": "editorially_corrob_with_external_reference",
            "independent_expert_review": False,
            "identity_review_scope": "this_direct_relation_only",
            "inference_eligible": False,
            "proof_eligible": False,
            "source_archive_sha256": json.loads((V1 / "manifest.json").read_text())["input_sha256"],
            "evidence_urls": [ref],
            "scope_note": "Specific ADT/Boolean claim corroborated by a separate educational/standards reference; no claim of formal proof or expert peer review.",
        })
    if len(stmt) != 126 or len(reviews) != 126 or len({s["id"] for s in stmt}) != len(stmt):
        raise ValueError("Expected 126 independently keyed admitted statements")
    for candidate in stmt:
        prev = original.get(candidate["id"])
        if prev is not None and prev != candidate:
            raise ValueError("Statement UUID collision with a different canonical assertion")
    if len({(s["subject"]["id"],s["predicate"],s["object"]["id"]) for s in stmt}) != len(stmt):
        raise ValueError("Duplicate admitted semantic triples")
    if any(x["inference_eligible"] or x["proof_eligible"] or x["independent_expert_review"] for x in reviews):
        raise ValueError("Invalid admission trust level")
    return stmt, reviews

def compact(rows):
    return "".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in rows)

def apply(*, write=False):
    existing_concepts = list(records(ROOT / "knowledge/concepts.jsonl"))
    existing_statements = list(records(ROOT / "knowledge/statements.jsonl"))
    generated, ledger = build(existing_concepts, existing_statements)
    policy = [
        {**p,
         "source_tier": "editorially_screened_direct_or_externally_corrob",
         "transitive": False, "symmetric": False,
         "safe_for_subtype_inference": False,
         "safe_for_prerequisite_inference": False,
         "safe_for_formal_proof": False}
        for p in PREDICATE_POLICIES
    ]
    result = {
        "schema": "curricula.semantic-admission@1",
        "input_source_version": ["cso@3.5","curricula-historical-v1@1.0.0"],
        "new_predicates": len(policy), "new_statements": len(generated),
        "admission_waves": {"wave1": 101, "wave2": 25},
        "wave2_explicitly_held_relations": 10,
        "source_cso_topic_relations": sum(x["source_id"] == CSO_ID for x in ledger),
        "externally_corrob_historical_core": sum(x["source_id"] == V1_ID for x in ledger),
        "proof_eligible_statement_count": 0,
        "independent_expert_reviewed_statement_count": 0,
        "source_relations_not_promoted": 153963 - len(generated),
    }
    if write:
        branch = subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
        if branch != "feat/semantic-admission-wave1":
            raise ValueError("Writes require the exact semantic admission feature branch")
        root_pred = ROOT / "knowledge/predicates.jsonl"
        orig_pred = list(records(root_pred))
        pred_slugs = {row["slug"] for row in orig_pred}
        root_pred.write_text(compact(sorted([*orig_pred,*[{"slug":p["slug"],"label":p["label"]} for p in policy if p["slug"] not in pred_slugs]], key=lambda x:x["slug"])))
        root_stmt = ROOT / "knowledge/statements.jsonl"
        orig_ids = {row["id"] for row in existing_statements}
        root_stmt.write_text(compact(sorted([*existing_statements,*[row for row in generated if row["id"] not in orig_ids]],key=lambda x:x["id"])))
        (ROOT / "knowledge/statement-admissions.jsonl").write_text(compact(sorted(ledger,key=lambda x:x["statement_id"])))
        (ROOT / "knowledge/predicate-policies.jsonl").write_text(compact(sorted(policy,key=lambda x:x["slug"])))
        (AREA / "admission-manifest.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--apply-to-feature-branch",action="store_true")
    opts=p.parse_args()
    print(json.dumps(apply(write=opts.apply_to_feature_branch),indent=2))
