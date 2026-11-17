import argparse,json
from collections import Counter
from reconcile_source_relations import ROOT,OUT,CSO,records

def review(slug,limit=30):
    if not 1<=limit<=100: raise ValueError("invalid limit")
    concepts={x["slug"]:x for x in records(ROOT/"knowledge/concepts.jsonl")}
    if slug not in concepts: raise ValueError("Unknown concept")
    target=concepts[slug]
    uid=target["id"]
    hist=[]
    hc=Counter()
    for x in records(OUT/"historical-statement-proposals.jsonl"):
        if uid in (x["subject_candidate_concept_id"],x["object_candidate_concept_id"]):
            hc[x["native_predicate"]]+=1
            if len(hist)<limit:hist.append(x)
    csouris={x["source_uri"] for x in records(CSO/"canonical-identity-candidates.jsonl") if uid in x["canonical_candidate_ids"]}
    cedges=[];cc=Counter()
    if csouris:
        for x in records(OUT/"cso-statement-proposals.jsonl.gz"):
            if x["subject_source_uri"] in csouris or x["object_source_uri"] in csouris:
                cc[x["native_predicate"]]+=1
                if len(cedges)<limit:cedges.append(x)
    return {"concept":target,"status":"unreviewed_source_candidate",
      "historical":{"count":sum(hc.values()),"predicate_counts":dict(hc),"sample":hist},
      "cso":{"candidate_source_uris":sorted(csouris),"identity_approved":False,
             "count":sum(cc.values()),"predicate_counts":dict(cc),"sample":cedges},
      "inference_eligible":False,"cross_source_identity_approved":False}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("slug");p.add_argument("--limit",type=int,default=12)
    a=p.parse_args()
    print(json.dumps(review(a.slug,a.limit),indent=2,ensure_ascii=False))
