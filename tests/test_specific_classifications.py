import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_specific_classifications_have_exact_premises_and_evidence():
    reviews = [json.loads(l) for l in (ROOT / 'pipeline/classification-review/specific-computing-classes.jsonl').read_text().splitlines()]
    concepts = {r['slug']: r['id'] for r in map(json.loads, (ROOT / 'knowledge/concepts.jsonl').read_text().splitlines())}
    statements = {r['id']: r for r in map(json.loads, (ROOT / 'knowledge/statements.jsonl').read_text().splitlines())}
    assert reviews
    for r in reviews:
        s = statements[r['statement_id']]
        assert (s['subject']['id'], s['predicate'], s['object']['id']) == (concepts[r['subject_slug']], 'subtype_of', concepts[r['object_slug']])
        assert r['evidence_urls'] and all(u.startswith('https://') for u in r['evidence_urls'])
        assert r['review_reason'] and r['scope']
        assert r['historical_edge_automatically_promoted'] is False
        assert r['independent_expert_review'] is False
    pairs = {(r['subject_slug'],r['object_slug']) for r in reviews}
    assert ('binary-coded-decimal','encoding') in pairs
    assert ('binary-coded-decimal','numeric-representation') in pairs
    assert ('numeric-representation','data-representation') in pairs
    assert ('file-read','file-operation') in pairs
    assert ('file-operation','computational-operation') in pairs
