"""Propose identity-only canonical concepts from the frozen, user-authored V1 source.

This operation never promotes old relations, definitions or curriculum overlays.
An addition is a draft identity proposal requiring a reviewed PR, not an
assertion that its historical scientific content was validated.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "knowledge/concepts.jsonl"
TERMS = ROOT / "sources/historical-v1/terms.jsonl"
LEDGER = ROOT / "pipeline/historical-v1-identity-proposals.jsonl"

def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def slugify(text):
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"(^-+|-+$)", "", re.sub(r"[^a-z0-9]+", "-", ascii_text))

def proposal_uuid(uri):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "curricula.live:historical-v1-provisional:" + uri))

def build(original, terms):
    by_slug = {row["slug"]: row for row in original}
    by_label = {" ".join(row["label"].casefold().split()): row for row in original}
    by_id = {row["id"]: row for row in original}
    if len(by_slug) != len(original) or len(by_id) != len(original):
        raise ValueError("Invalid canonical baseline")
    added, decisions = [], []
    seen_sources = set()
    for term in sorted(terms, key=lambda t: t["source_uri"]):
        uri, label = term["source_uri"], term["label"]
        if uri in seen_sources:
            raise ValueError("Duplicate source URI")
        seen_sources.add(uri)
        key = " ".join(label.casefold().split())
        slug = slugify(label)
        proposed_id = proposal_uuid(uri)
        entry = {
            "source_uri": uri, "source_label": label,
            "source_version": "archived-v1.0.0", "review_status": "proposed_not_approved",
            "statement_imported": False, "source_identity_is_canonical": False,
        }
        if key in by_label:
            match = by_label[key]
            entry.update({"decision": "exact_label_candidate", "candidate_id": match["id"]})
            # In the idempotent rerun case the deterministic newly authored identity
            # stays in the ledger as a provisional proposal rather than source authority.
            if match["id"] == proposed_id:
                entry["decision"] = "proposed_concept_on_branch"
        elif not slug or len(slug) > 160 or len(label) > 240:
            entry.update({"decision": "unsupported_slug_or_length"})
        elif slug in by_slug or proposed_id in by_id:
            entry.update({"decision": "slug_or_id_collision", "candidate_slug": slug})
        else:
            row = {"id": proposed_id, "slug": slug, "label": label}
            added.append(row)
            by_slug[slug] = row
            by_id[proposed_id] = row
            by_label[key] = row
            entry.update({"decision": "proposed_concept_on_branch",
                          "candidate_id": proposed_id, "candidate_slug": slug})
        decisions.append(entry)
    return sorted([*original, *added], key=lambda item: item["slug"]), decisions, added

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply-to-feature-branch", action="store_true")
    a = p.parse_args()
    records, decisions, added = build(load(CONCEPTS), load(TERMS))
    counts = {d: sum(x["decision"] == d for x in decisions) for d in sorted(set(x["decision"] for x in decisions))}
    if a.apply_to_feature_branch:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        if not branch.startswith("feat/"):
            raise ValueError("Proposals may only be written on a feature branch")
        CONCEPTS.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in records))
        LEDGER.parent.mkdir(exist_ok=True)
        LEDGER.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in decisions))
    print(json.dumps({"additions": len(added), "resulting_canonical_proposal_count": len(records),
                      "decisions": counts, "wrote_to_feature_branch": a.apply_to_feature_branch}, indent=2))

if __name__ == "__main__":
    main()
