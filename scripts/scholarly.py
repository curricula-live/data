"""Offline, deterministic scholarly ingestion. Never writes the canonical graph or DB."""
import argparse
import hashlib
import json
import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.parse import urlparse

PIPELINE_VERSION = 1
STATUSES = {'candidate', 'approved', 'rejected'}
KINDS = {'classification', 'knowledge_area', 'knowledge_unit', 'topic', 'learning_outcome',
         'standard', 'grade_band', 'concept', 'subconcept', 'practice'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def reference(ref):
    require(isinstance(ref, dict) and nonempty(ref.get('locator')) and
            nonempty(ref.get('document_sha256')), 'reference requires document checksum and locator')
    require(re.fullmatch(r'[0-9a-f]{64}', ref['document_sha256']), 'invalid reference checksum')


def reviewed(row):
    require(row.get('status') in STATUSES, 'invalid review status')
    if row['status'] == 'approved':
        r = row.get('review', {})
        require(all(nonempty(r.get(k)) for k in ('reviewer', 'date', 'rationale')), 'approval requires review evidence')
        date.fromisoformat(r['date'])
        require(bool(row.get('references')), 'approval requires references')
    for ref in row.get('references', []):
        reference(ref)


def validate(bundle):
    require(bundle.get('schema_version') == 1, 'unsupported schema version')
    source = bundle['source']
    for key in ('id', 'version', 'publisher', 'url', 'retrieved_on', 'license', 'publication_scope'):
        require(nonempty(source.get(key)), f'missing source {key}')
    require(source['id'] in {'acm-ccs', 'cs2023', 'csta'}, 'unknown source')
    date.fromisoformat(source['retrieved_on'])
    require(bool(re.fullmatch(r'[A-Za-z0-9._-]+', source['version'])), 'version must be URL-safe')
    require(urlparse(source['url']).scheme == 'https' and bool(urlparse(source['url']).netloc), 'source URL must be HTTPS')
    require(source['publication_scope'] in {'restricted', 'metadata-only', 'public'}, 'invalid publication scope')
    require(re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', '')), 'source bytes checksum required')
    require(source.get('distribution') in {'official', 'third-party'}, 'distribution provenance required')
    nodes = bundle['nodes']
    by_id = {n['id']: n for n in nodes}
    require(len(by_id) == len(nodes), 'duplicate external identifier')
    require(bool(nodes), 'empty taxonomy')
    for n in nodes:
        require(nonempty(n.get('id')) and nonempty(n.get('label')), 'missing node identity/label')
        require(n.get('kind') in KINDS, 'invalid node kind')
        require(isinstance(n.get('parents'), list), 'explicit parents required')
        require(len(set(n['parents'])) == len(n['parents']), 'duplicate parent')
        require(nonempty(n.get('locator')), 'source locator required')
        for p in n['parents']:
            require(p in by_id, f'orphan parent {p}')
        if source['id'] == 'cs2023':
            allowed = {'knowledge_area': set(), 'knowledge_unit': {'knowledge_area'},
                       'topic': {'knowledge_unit', 'topic'}, 'learning_outcome': {'knowledge_unit'}}
            require(n['kind'] in allowed, 'invalid CS2023 entity')
            require(all(by_id[p]['kind'] in allowed[n['kind']] for p in n['parents']), 'invalid CS2023 hierarchy')
            require(n['kind'] == 'knowledge_area' or bool(n['parents']), 'orphan curriculum entity')
            if n['kind'] == 'topic':
                require(n.get('core') in {'CS Core', 'KA Core', 'Non-core'}, 'topic core classification required')
            for outcome in n.get('learning_outcomes', []):
                require(outcome in by_id and by_id[outcome]['kind'] == 'learning_outcome', 'unknown learning outcome')
        if source['id'] == 'csta' and n['kind'] == 'standard':
            require(source['version'] == '2017', 'only CSTA 2017 standard parsing is supported')
            require(re.fullmatch(r'(1A|1B|2|3A|3B)-(AP|CS|DA|IC|NI)-\d{2}', n['id']), 'invalid 2017 standard ID')
            for key in ('grade_band', 'concept', 'subconcept', 'practices'):
                require(bool(n.get(key)), f'missing CSTA {key}')
            require(isinstance(n['practices'], list), 'practices must be a list')
    # Kahn traversal avoids recursion limits on deep or malicious input.
    pending = {k: len(n['parents']) for k, n in by_id.items()}
    children = {k: [] for k in by_id}
    for n in nodes:
        for p in n['parents']:
            children[p].append(n['id'])
    queue = [k for k, count in pending.items() if count == 0]
    visited = 0
    while queue:
        key = queue.pop()
        visited += 1
        for child in children[key]:
            pending[child] -= 1
            if pending[child] == 0:
                queue.append(child)
    require(visited == len(nodes), 'taxonomy cycle')
    require(bundle.get('completeness') in {'partial', 'complete'}, 'explicit completeness required')
    if bundle['completeness'] == 'complete':
        require(source.get('expected_nodes') == len(nodes), 'complete import requires independently recorded expected count')
    seen = set()
    for m in bundle.get('mappings', []):
        reviewed(m)
        require(m.get('node_id') in by_id, 'mapping node missing')
        uuid.UUID(m['canonical_uuid'])
        require(nonempty(m.get('canonical_slug')), 'mapping slug required')
        require(m.get('relation') in {'exact', 'close', 'related', 'curriculum_association'}, 'invalid mapping relation')
        require(isinstance(m.get('confidence'), (int, float)) and 0 <= m['confidence'] <= 1, 'invalid confidence')
        key = (m['node_id'], m['canonical_uuid'], m['relation'])
        require(key not in seen, 'duplicate mapping')
        seen.add(key)
    seen = set()
    for d in bundle.get('definitions', []):
        reviewed(d)
        uuid.UUID(d['canonical_uuid'])
        require(d.get('kind') in {'editorial', 'quotation', 'paraphrase', 'conflicting'}, 'invalid definition kind')
        for key in ('id', 'text', 'author', 'license', 'publication_scope', 'canonical_slug'):
            require(nonempty(d.get(key)), f'missing definition {key}')
        require(d['publication_scope'] in {'restricted', 'public'}, 'invalid definition publication scope')
        require(isinstance(d.get('revision'), int) and d['revision'] > 0, 'definition revision required')
        require(d['id'] not in seen, 'duplicate definition ID')
        seen.add(d['id'])
        require(isinstance(d.get('history'), list) and len(d['history']) == d['revision'], 'definition history required for every revision')
        require([h.get('revision') for h in d['history']] == list(range(1, d['revision'] + 1)), 'history revisions must be contiguous')
        for entry in d['history']:
            date.fromisoformat(entry['date'])
            require(nonempty(entry.get('action')), 'history action required')
        if d.get('ai_assisted'):
            require(d.get('externally_verified') is not True, 'AI text cannot be marked externally verified')
    # References must resolve to this exact document or explicit additional document inventory.
    documents = {source['sha256']} | {d['sha256'] for d in bundle.get('documents', [])}
    for row in bundle.get('mappings', []) + bundle.get('definitions', []):
        for ref in row.get('references', []):
            require(ref['document_sha256'] in documents, 'unregistered reference document')
    return bundle


def import_skos(raw):
    """SKOS/RDF-XML adapter. Author selection CCSXML is deliberately unsupported."""
    require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'DTD/entities forbidden')
    root = ET.fromstring(raw)
    ns = {'s': 'http://www.w3.org/2004/02/skos/core#', 'r': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
    about = '{' + ns['r'] + '}about'
    resource = '{' + ns['r'] + '}resource'
    nodes = []
    for element in root.findall('.//s:Concept', ns):
        labels = element.findall('s:prefLabel', ns)
        label = next((x.text for x in labels if x.get('{http://www.w3.org/XML/1998/namespace}lang') == 'en'), None)
        if label is None and len(labels) == 1:
            label = labels[0].text
        key = element.get(about)
        nodes.append({'id': key, 'label': label, 'kind': 'classification',
                      'parents': [p.get(resource) for p in element.findall('s:broader', ns)], 'locator': key})
    require(bool(nodes), 'not a supported SKOS taxonomy; no concepts found')
    # Some official RDF distributions express hierarchy using narrower only.
    by_id = {n['id']: n for n in nodes}
    require(len(by_id) == len(nodes), 'duplicate SKOS identifier')
    for element in root.findall('.//s:Concept', ns):
        for child in element.findall('s:narrower', ns):
            key = child.get(resource)
            require(key in by_id, 'orphan narrower reference')
            parent = element.get(about)
            if parent not in by_id[key]['parents']:
                by_id[key]['parents'].append(parent)
    return nodes


def normalized(label):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', label).casefold()))


def candidates(bundle, canonical):
    """Input must be a verified UUID export; seed slugs are insufficient."""
    labels = {}
    for c in canonical:
        uuid.UUID(c['id'])
        labels.setdefault(normalized(c['label']), []).append(c)
    result = []
    for node in bundle['nodes']:
        for c in labels.get(normalized(node['label']), []):
            result.append({'node_id': node['id'], 'canonical_uuid': c['id'], 'canonical_slug': c['slug'],
                           'relation': 'related', 'confidence': 0.5, 'status': 'candidate',
                           'method': 'exact_normalized_label_v1', 'references': [{'document_sha256': bundle['source']['sha256'],
                                                                                'locator': node['locator']}]})
    return sorted(result, key=lambda m: (m['node_id'], m['canonical_uuid']))


def public_export(bundle):
    validate(bundle)
    source = bundle['source']
    require(source['publication_scope'] == 'public' and source['distribution'] == 'official', 'source publication not permitted')
    permission = source.get('permission', {})
    require(all(nonempty(permission.get(k)) for k in ('reviewer', 'date', 'evidence_url', 'scope')), 'publication permission review required')
    require(permission['scope'] == 'public-commercial-redistribution', 'permission scope insufficient')
    date.fromisoformat(permission['date'])
    require(bundle.get('source_review', {}).get('status') == 'approved', 'source import review required')
    require(all(nonempty(bundle['source_review'].get(k)) for k in ('reviewer', 'date', 'rationale')), 'source review evidence required')
    # Explicit allowlists prevent leaking restricted notes or draft content.
    clean = {k: source[k] for k in ('id', 'version', 'publisher', 'url', 'retrieved_on', 'license', 'sha256', 'publication_scope', 'distribution', 'permission')}
    mappings = [m for m in bundle.get('mappings', []) if m['status'] == 'approved']
    definitions = [d for d in bundle.get('definitions', []) if d['status'] == 'approved' and d['publication_scope'] == 'public']
    # Public text must carry its own publication permission, even for editorial work.
    for d in definitions:
        require(nonempty(d.get('permission_evidence')), 'definition publication permission required')
    node_keys = {'id', 'label', 'kind', 'parents', 'locator', 'abbreviation', 'official_id', 'core',
                 'learning_outcomes', 'grade_band', 'concept', 'subconcept', 'practices'}
    mapping_keys = {'node_id', 'canonical_uuid', 'canonical_slug', 'relation', 'confidence', 'status', 'method', 'references', 'review'}
    definition_keys = {'id', 'canonical_uuid', 'canonical_slug', 'text', 'author', 'kind', 'license', 'publication_scope',
                       'revision', 'history', 'status', 'references', 'review', 'permission_evidence', 'ai_assisted', 'externally_verified'}
    return {'schema_version': 1, 'source': clean, 'completeness': bundle['completeness'],
            'source_review': bundle['source_review'], 'documents': [{k: d[k] for k in ('sha256', 'url', 'publisher', 'license') if k in d} for d in bundle.get('documents', [])],
            'nodes': [{k: n[k] for k in node_keys if k in n} for n in sorted(bundle['nodes'], key=lambda n: n['id'])],
            'mappings': [{k: m[k] for k in mapping_keys if k in m} for m in sorted(mappings, key=lambda m: (m['node_id'], m['canonical_uuid'], m['relation']))],
            'definitions': [{k: d[k] for k in definition_keys if k in d} for d in sorted(definitions, key=lambda d: d['id'])]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    imp = sub.add_parser('import')
    imp.add_argument('--manifest', type=Path, required=True)
    imp.add_argument('--input', type=Path, required=True)
    imp.add_argument('--format', choices=['skos', 'curated-json'], required=True)
    imp.add_argument('--output', type=Path, required=True)
    imp.add_argument('--completeness', choices=['partial', 'complete'], default='partial')
    for name in ('check', 'export', 'candidates', 'coverage'):
        p = sub.add_parser(name)
        p.add_argument('bundle', type=Path)
        if name in ('export', 'candidates'):
            p.add_argument('--output', type=Path, required=True)
        if name == 'candidates':
            p.add_argument('--canonical', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'import':
        source = json.loads(args.manifest.read_text())
        raw = args.input.read_bytes()
        require(source['sha256'] == digest(raw), 'source checksum mismatch')
        nodes = import_skos(raw) if args.format == 'skos' else json.loads(raw)
        for n in nodes:
            n['parents'] = sorted(n['parents'])
        bundle = {'schema_version': 1, 'source': source, 'completeness': args.completeness,
                  'nodes': sorted(nodes, key=lambda n: n['id']), 'mappings': [], 'definitions': [],
                  'import_history': [{'source_sha256': source['sha256'], 'pipeline_version': PIPELINE_VERSION,
                                      'format': args.format, 'node_count': len(nodes)}]}
        validate(bundle)
        args.output.write_bytes(encode(bundle))
        return
    bundle = validate(json.loads(args.bundle.read_text()))
    if args.command == 'export':
        args.output.write_bytes(encode(public_export(bundle)))
    elif args.command == 'candidates':
        canonical = [json.loads(line) for line in args.canonical.read_text().splitlines() if line]
        args.output.write_bytes(encode(candidates(bundle, canonical)))
    elif args.command == 'coverage':
        print(json.dumps({'imported_source_records': len(bundle['nodes']), 'completeness': bundle['completeness'],
                          'candidate_associations': sum(m['status'] == 'candidate' for m in bundle['mappings']),
                          'mapped_canonical_concepts': len({m['canonical_uuid'] for m in bundle['mappings'] if m['status'] == 'approved'}),
                          'canonical_concepts_with_candidates': len({m['canonical_uuid'] for m in bundle['mappings'] if m['status'] == 'candidate'}),
                          'reviewed_approved_mappings': sum(m['status'] == 'approved' for m in bundle['mappings']),
                          'attested_definitions': sum(d['status'] == 'approved' for d in bundle['definitions']),
                          'published_records': 'not measured; inspect installed API release'}, sort_keys=True))
    else:
        print('valid')


if __name__ == '__main__':
    main()
