"""Source-preserving reconciliation of every historic/CSO relation.

Outputs are candidate assertion records with canonical UUID mapping proposals,
not approved scientific facts, canonical statements, or inference premises.
All source predicates stay distinct. No equivalence/subtype/prerequisite inference.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "source-reconciliation"
V1 = ROOT / "sources/historical-v1"
CSO = ROOT / "sources/cso-3.5"
V1_ID = "curricula-historical-v1@1.0.0"
CSO_ID = "cso@3.5"
V1_PREDICATES = {
    "broaderTopic": ("historical_topic_broader_than", "topic_hierarchy", "Historical broader-topic classification"),
    "hasOperation": ("historical_has_operation", "recorded_association", "Historical has-operation association"),
    "hasProperty": ("historical_has_property", "recorded_association", "Historical has-property association"),
    "implements": ("historical_implements", "recorded_association", "Historical implements association"),
    "subtopicOf": ("historical_subtopic_of", "topic_hierarchy", "Historical subtopic classification"),
    "valueOfType": ("historical_value_of_type", "recorded_association", "Historical value-of-type association"),
}
CSO_PREDICATES = {
    "http://cso.kmi.open.ac.uk/schema/cso#contributesTo": ("cso_contributes_to", "topic_association", "CSO research-area topical contribution"),
    "http://cso.kmi.open.ac.uk/schema/cso#superTopicOf": ("cso_super_topic_of", "topic_hierarchy", "CSO broader research area to narrower topic"),
    "http://cso.kmi.open.ac.uk/schema/cso#relatedEquivalent": ("cso_related_equivalent", "source_equivalence_claim", "CSO related equivalence claim"),
    "http://cso.kmi.open.ac.uk/schema/cso#preferentialEquivalent": ("cso_preferential_equivalent", "source_equivalence_claim", "CSO preferential equivalent label"),
    "http://www.w3.org/2002/07/owl#sameAs": ("cso_owl_same_as", "source_equivalence_claim", "CSO owl:sameAs source assertion"),
    "http://schema.org/relatedLink": ("cso_related_link", "external_reference", "CSO external related link"),
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": ("cso_rdf_type", "source_type_record", "CSO RDF class designation"),
    "http://www.w3.org/2000/01/rdf-schema#label": ("cso_label", "source_label", "CSO source English label"),
}

def records(path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)

def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def uri_witness(s, p, o):
    return "sha256:" + hashlib.sha256((f"<{s}> <{p}> <{o}> .").encode("utf-8")).hexdigest()

def predicate_catalog():
    entries = []
    for source_id, table in ((V1_ID, V1_PREDICATES), (CSO_ID, CSO_PREDICATES)):
        for native, (proposal, semantic, summary) in sorted(table.items()):
            entries.append({
                "source_id": source_id, "native_predicate": native,
                "proposed_predicate_slug": proposal, "semantic_family": semantic,
                "description": summary, "review_status": "unreviewed_source_mapping",
                "canonical_predicate_approved": False,
                "safe_for_subtype_inference": False,
                "safe_for_learning_prerequisite_inference": False,
                "automatic_identity_equivalence": False,
            })
    return entries

def mapping_for_v1():
    mapping = {}
    for row in records(ROOT / "pipeline/historical-v1-identity-proposals.jsonl"):
        if row["source_uri"] in mapping:
            raise ValueError("Duplicate source identity")
        mapping[row["source_uri"]] = row
    return mapping

def mapping_for_cso():
    result = defaultdict(set)
    for row in records(CSO / "canonical-identity-candidates.jsonl"):
        result[row["source_uri"]].update(row["canonical_candidate_ids"])
    return {key: sorted(values) for key, values in result.items()}

def reconcile_historical(mapping, path):
    counts = Counter()
    by_predicate = Counter()
    seen = set()
    edges = 0
    with path.open("wb") as f:
        for edge in records(V1 / "relations.jsonl"):
            source, target = mapping.get(edge["subject_uri"]), mapping.get(edge["object_uri"])
            if source is None or target is None:
                raise ValueError("Incomplete historic identity ledger")
            uri = edge["assertion_id"]
            if uri in seen:
                raise ValueError("Duplicate historical assertion")
            seen.add(uri)
            p = edge["predicate"]
            if p not in V1_PREDICATES:
                raise ValueError("Unmapped historical predicate " + p)
            categories = (source["decision"], target["decision"])
            if "slug_or_id_collision" in categories or "unsupported_slug_or_length" in categories:
                review = "blocked_identity_collision"
            elif all(v == "proposed_concept_on_branch" for v in categories):
                review = "two_provisional_ids_mapped"
            else:
                review = "requires_existing_concept_identity_approval"
            candidate = None
            if review == "two_provisional_ids_mapped":
                # This intentionally remains a PROPOSAL. A future approved
                # admission may use these stable UUIDs as source-scoped witnesses.
                candidate = {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "curricula:data:historical-assertion-candidate:" + uri)),
                    "subject": {"kind": "concept", "id": source["candidate_id"]},
                    "predicate": V1_PREDICATES[p][0],
                    "object": {"kind": "concept", "id": target["candidate_id"]},
                }
            result = {
                "source_id": V1_ID, "source_assertion_uri": uri,
                "subject_source_uri": edge["subject_uri"], "object_source_uri": edge["object_uri"],
                "native_predicate": p, "predicate_candidate_slug": V1_PREDICATES[p][0],
                "native_assertion_status": edge["assertion_status"],
                "subject_candidate_concept_id": source.get("candidate_id"),
                "object_candidate_concept_id": target.get("candidate_id"),
                "subject_mapping_decision": source["decision"],
                "object_mapping_decision": target["decision"],
                "reconciliation_status": review,
                "proposed_statement": candidate,
                "accepted_canonical_statement": False,
                "evidence_witness": uri,
                "inference_eligible": False,
            }
            f.write(encode(result))
            counts[review] += 1
            by_predicate[p] += 1
            edges += 1
    return {"processed": edges, "statuses": dict(sorted(counts.items())),
            "predicates": dict(sorted(by_predicate.items()))}

def reconcile_cso(mapping, path):
    known = {t["uri"] for t in records(CSO / "topics.jsonl")}
    counts, by_predicate, map_degree = Counter(), Counter(), Counter()
    seen = set()
    edges = 0
    with path.open("wb") as f:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, mtime=0, fileobj=f) as gz:
            for edge in records(CSO / "uri-relations.jsonl.gz"):
                s, p, o = edge["subject_uri"], edge["predicate_uri"], edge["object_uri"]
                if p not in CSO_PREDICATES:
                    raise ValueError("Unmapped CSO predicate " + p)
                witness = uri_witness(s, p, o)
                if witness in seen:
                    raise ValueError("Duplicate CSO source triple")
                seen.add(witness)
                sc, oc = mapping.get(s, []), mapping.get(o, [])
                if s not in known:
                    status = "unlabelled_subject_or_external"
                elif o not in known:
                    status = "source_or_external_object_unmapped"
                elif sc and oc:
                    status = "both_lexical_candidates_require_review"
                elif sc or oc:
                    status = "one_lexical_candidate_requires_review"
                else:
                    status = "source_only_no_canonical_identity"
                result = {
                    "source_id": CSO_ID,
                    "source_assertion_uri": witness,
                    "subject_source_uri": s, "native_predicate": p,
                    "object_source_uri": o,
                    "predicate_candidate_slug": CSO_PREDICATES[p][0],
                    "subject_candidate_concept_ids": sc,
                    "object_candidate_concept_ids": oc,
                    "object_is_labelled_cso_topic": o in known,
                    "reconciliation_status": status,
                    "accepted_canonical_statement": False,
                    "proposed_statement": None,
                    "inference_eligible": False,
                }
                gz.write(encode(result))
                counts[status] += 1
                by_predicate[p] += 1
                map_degree[f"subject:{'mapped' if sc else 'unmapped'}"] += 1
                map_degree[f"object:{'mapped' if oc else 'unmapped'}"] += 1
                edges += 1
    return {"processed": edges, "statuses": dict(sorted(counts.items())),
            "predicates": dict(sorted(by_predicate.items())),
            "candidate_mapping_coverage": dict(sorted(map_degree.items()))}

def build_concept_index(output):
    """One explicit coverage record for every newly proposed canonical concept."""
    from collections import defaultdict
    decisions = [
        row for row in records(ROOT / "pipeline/historical-v1-identity-proposals.jsonl")
        if row["decision"] == "proposed_concept_on_branch"
    ]
    counts = defaultdict(Counter)
    samples = defaultdict(list)
    for item in records(output / "historical-statement-proposals.jsonl"):
        for side in ("subject", "object"):
            cid = item[f"{side}_candidate_concept_id"]
            if not cid:
                continue
            counts[cid][f"{side}_relation_count"] += 1
            counts[cid][f"{side}_status:{item['reconciliation_status']}"] += 1
            if len(samples[cid]) < 8:
                samples[cid].append(item["source_assertion_uri"])
    per_concept = []
    for row in sorted(decisions, key=lambda x: x["candidate_id"]):
        cid = row["candidate_id"]
        k = counts[cid]
        per_concept.append({
            "candidate_concept_id": cid,
            "candidate_slug": row["candidate_slug"],
            "label": row["source_label"],
            "historical_source_uri": row["source_uri"],
            "incoming_relation_candidates": k["object_relation_count"],
            "outgoing_relation_candidates": k["subject_relation_count"],
            "candidate_status_counts": {
                name.replace("subject_status:", ""): value
                for name, value in sorted(k.items()) if name.startswith("subject_status:")
            },
            "sample_source_assertion_uris": samples[cid],
            "review_state": "unreviewed_identity_and_statements",
            "canonical_inference_eligible": False,
        })
    with (output / "per-concept-coverage.jsonl").open("wb") as f:
        for row in per_concept:
            f.write(encode(row))
    connected = sum(bool(x["incoming_relation_candidates"] or x["outgoing_relation_candidates"])
                    for x in per_concept)
    return {"total_new_concepts": len(per_concept),
            "with_historical_relationship_candidates": connected,
            "without_historical_relationship_candidates": len(per_concept) - connected}


def build(output=OUT):
    output.mkdir(parents=True, exist_ok=True)
    predicates = predicate_catalog()
    if len(predicates) != 14 or len({x["proposed_predicate_slug"] for x in predicates}) != len(predicates):
        raise ValueError("Expected 14 distinct source-scoped predicate proposals")
    with (output / "predicate-proposals.jsonl").open("wb") as f:
        for row in predicates:
            f.write(encode(row))
    history = reconcile_historical(mapping_for_v1(), output / "historical-statement-proposals.jsonl")
    cso = reconcile_cso(mapping_for_cso(), output / "cso-statement-proposals.jsonl.gz")
    source_manifests = {
        "historical-v1": json.loads((V1 / "manifest.json").read_text()),
        "cso": json.loads((CSO / "manifest.json").read_text()),
    }
    if history["processed"] != source_manifests["historical-v1"]["uri_relation_count"]:
        raise ValueError("Historic source relation count drift")
    if cso["processed"] != source_manifests["cso"]["uri_relation_count"]:
        raise ValueError("CSO source relation count drift")
    per_concept_coverage = build_concept_index(output)
    manifest = {
        "schema": "curricula.source-reconciliation@1",
        "canonical_relation_type_promotions": 0,
        "canonical_statement_promotions": 0,
        "predicate_proposals": len(predicates),
        "all_sources_reconciled": True,
        "status": "proposed_unreviewed_inference_prohibited",
        "source_rows": {"historical-v1": history, "cso": cso},
        "new_concept_coverage": per_concept_coverage,
        "cross_source_identity_join_approved": False,
        "automatic_subtype_inference_enabled": False,
        "automatic_prerequisite_inference_enabled": False,
        "source_archive_hashes": {
            "historical-v1": source_manifests["historical-v1"]["input_sha256"],
            "cso": source_manifests["cso"]["archive_sha256"],
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))

if __name__ == "__main__":
    main()
