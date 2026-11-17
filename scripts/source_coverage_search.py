"""Read-only lookup across canonical concepts and source-scoped candidates."""
import argparse
import json
from pathlib import Path
from difflib import get_close_matches
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CATALOGUES = (
    ("canonical", ROOT / "knowledge/concepts.jsonl", "label", "slug", "canonical"),
    ("cso@3.5", ROOT / "sources/cso-3.5/topics.jsonl", "label", "uri", "source_only"),
    ("historical-v1", ROOT / "sources/historical-v1/terms.jsonl", "label", "source_uri", "unreviewed_historical"),
)

def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("c++", "cplusplus").replace("c#", "csharp")
    return " ".join(re.findall(r"[a-z0-9]+", text))

def search(query: str, limit: int = 25) -> dict:
    if not (1 <= len(query) <= 120 and 1 <= limit <= 100):
        raise ValueError("query must have 1..120 characters and limit 1..100")
    needle = normalized(query)
    if not needle:
        raise ValueError("query has no searchable characters")
    matches, labels = [], set()
    for source, path, label_key, id_key, state in CATALOGUES:
        for raw in path.open(encoding="utf-8"):
            if not raw.strip():
                continue
            item = json.loads(raw)
            label = normalized(item[label_key])
            labels.add(label)
            if needle in label:
                priority = 0 if label == needle else 1 if label.startswith(needle) else 2
                matches.append((priority, 0 if state == "canonical" else 1 if state == "source_only" else 2, len(label), label, {
                    "source": source, "label": item[label_key], "identifier": item.get(id_key),
                    "status": state,
                }))
    matches.sort(key=lambda x: x[:4])
    exact = any(x[0] == 0 for x in matches)
    return {
        "query": query,
        "lookup_status": "exact" if exact else "related_matches" if matches else "no_recorded_match",
        "canonical_exact": any(x[0] == 0 and x[1] == 0 for x in matches),
        "total_matches": len(matches), "results": [x[-1] for x in matches[:limit]],
        "spelling_suggestions": get_close_matches(needle, sorted(labels), n=8, cutoff=0.75) if not matches else [],
        "source_hits_are_canonical": False,
        "inference_from_source_candidates_allowed": False,
    }
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=25)
    a = p.parse_args()
    print(json.dumps(search(a.query, a.limit), indent=2, ensure_ascii=False))
