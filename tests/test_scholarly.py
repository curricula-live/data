import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.scholarly import candidates, digest, encode, import_skos, public_export, validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bundle():
    return {'schema_version': 1, 'source': {'id': 'acm-ccs', 'version': 'synthetic-test',
        'publisher': 'Test only', 'url': 'https://example.invalid/source', 'retrieved_on': '2026-10-15',
        'license': 'synthetic', 'publication_scope': 'restricted', 'sha256': 'a' * 64, 'distribution': 'official'},
        'completeness': 'partial', 'nodes': [
            {'id': 'root', 'label': 'Root', 'kind': 'classification', 'parents': [], 'locator': '#root'},
            {'id': 'child', 'label': 'Queue', 'kind': 'classification', 'parents': ['root'], 'locator': '#child'}],
        'mappings': [], 'definitions': []}


def test_hierarchy_errors(bundle):
    validate(bundle)
    for mutate, message in [
        (lambda b: b['nodes'].append(copy.deepcopy(b['nodes'][0])), 'duplicate'),
        (lambda b: b['nodes'][1].update(parents=['absent']), 'orphan'),
        (lambda b: b['nodes'][0].update(parents=['child']), 'cycle'),
        (lambda b: b.update(completeness='complete'), 'expected count'),
    ]:
        broken = copy.deepcopy(bundle)
        mutate(broken)
        with pytest.raises(ValueError, match=message):
            validate(broken)


def test_label_matches_are_never_approvals(bundle):
    result = candidates(bundle, [{'id': 'b2c3592c-3ea4-4423-927e-287f43c9aa57', 'label': 'Ｑｕｅｕｅ', 'slug': 'queue'}])
    assert len(result) == 1
    assert result[0]['status'] == 'candidate'
    assert result[0]['relation'] == 'related'
    bundle['mappings'] = result
    validate(bundle)
    bundle['mappings'][0]['status'] = 'approved'
    with pytest.raises(ValueError, match='review evidence'):
        validate(bundle)
    with pytest.raises(KeyError):
        candidates(bundle, [{'slug': 'queue', 'label': 'Queue'}])


def permit(bundle):
    bundle['source']['publication_scope'] = 'public'
    bundle['source']['permission'] = {'reviewer': 'Test reviewer', 'date': '2026-10-15',
        'evidence_url': 'https://example.invalid/permission', 'scope': 'public-commercial-redistribution'}
    bundle['source_review'] = {'status': 'approved', 'reviewer': 'Test reviewer', 'date': '2026-10-15', 'rationale': 'Synthetic fixture'}


def test_publication_boundaries(bundle):
    with pytest.raises(ValueError, match='not permitted'):
        public_export(bundle)
    permit(bundle)
    bundle['nodes'][0]['private_note'] = 'secret'
    bundle['mappings'] = candidates(bundle, [{'id': 'b2c3592c-3ea4-4423-927e-287f43c9aa57', 'label': 'Queue', 'slug': 'queue'}])
    exported = public_export(bundle)
    assert exported['mappings'] == []
    assert 'secret' not in encode(exported).decode()
    assert public_export(exported) == exported
    bundle['source']['distribution'] = 'third-party'
    with pytest.raises(ValueError, match='not permitted'):
        public_export(bundle)


def test_skos_broader_narrower_and_duplicate_labels():
    raw = b'''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:s="http://www.w3.org/2004/02/skos/core#">
    <s:Concept rdf:about="r"><s:prefLabel xml:lang="en">Same</s:prefLabel><s:narrower rdf:resource="c"/></s:Concept>
    <s:Concept rdf:about="c"><s:prefLabel xml:lang="en">Same</s:prefLabel><s:broader rdf:resource="r"/></s:Concept></rdf:RDF>'''
    nodes = import_skos(raw)
    assert nodes[1]['parents'] == ['r']
    assert nodes[0]['id'] != nodes[1]['id']
    with pytest.raises(ValueError):
        import_skos(b'<!DOCTYPE a><ccs2012/>')
    with pytest.raises(ValueError, match='no concepts'):
        import_skos(b'<ccs2012><concept/></ccs2012>')


def test_reproducible_idempotent_import(bundle, tmp_path):
    source_file = tmp_path / 'source.json'
    manifest = tmp_path / 'manifest.json'
    output = tmp_path / 'bundle.json'
    source_file.write_bytes(encode(bundle['nodes']))
    bundle['source']['sha256'] = digest(source_file.read_bytes())
    manifest.write_bytes(encode(bundle['source']))
    command = [sys.executable, str(ROOT / 'scripts/scholarly.py'), 'import', '--manifest', str(manifest),
               '--input', str(source_file), '--format', 'curated-json', '--output', str(output)]
    subprocess.run(command, check=True)
    first = output.read_bytes()
    subprocess.run(command, check=True)
    assert output.read_bytes() == first
    source_file.write_text('[]')
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == first


def test_cs2023_keeps_core_and_outcomes(bundle):
    bundle['source']['id'] = 'cs2023'
    bundle['nodes'] = [
        {'id': 'AL', 'label': 'Area', 'kind': 'knowledge_area', 'parents': [], 'locator': 'p1'},
        {'id': 'AL-U', 'label': 'Unit', 'kind': 'knowledge_unit', 'parents': ['AL'], 'locator': 'p2'},
        {'id': 'editorial:p2:t1', 'official_id': None, 'label': 'Topic', 'kind': 'topic', 'core': 'CS Core',
         'parents': ['AL-U'], 'locator': 'p2 topic 1', 'learning_outcomes': ['editorial:p2:lo1']},
        {'id': 'editorial:p2:lo1', 'label': 'Outcome', 'kind': 'learning_outcome', 'parents': ['AL-U'], 'locator': 'p2 outcome 1'}]
    validate(bundle)
    bundle['nodes'][2]['parents'] = ['AL']
    with pytest.raises(ValueError, match='hierarchy'):
        validate(bundle)


def test_csta_fields_and_version_are_not_assumed(bundle):
    bundle['source'].update(id='csta', version='2017', publication_scope='metadata-only')
    bundle['nodes'] = [{'id': '1A-CS-01', 'label': 'Synthetic standard', 'kind': 'standard', 'parents': [],
                        'locator': 'p4', 'grade_band': 'K-2', 'concept': 'CS', 'subconcept': 'Devices', 'practices': ['1.1']}]
    validate(bundle)
    with pytest.raises(ValueError, match='not permitted'):
        public_export(bundle)
    bundle['source']['version'] = '2026'
    with pytest.raises(ValueError, match='only CSTA 2017'):
        validate(bundle)


def test_definition_attestation_and_ai_review_boundary(bundle):
    permit(bundle)
    definition = {'id': 'queue-v1', 'canonical_uuid': 'b2c3592c-3ea4-4423-927e-287f43c9aa57',
        'canonical_slug': 'queue', 'text': 'Synthetic definition.', 'kind': 'editorial', 'author': 'Synthetic author',
        'license': 'Test only', 'publication_scope': 'public', 'revision': 1,
        'history': [{'revision': 1, 'date': '2026-10-15', 'action': 'Synthetic fixture'}],
        'status': 'approved', 'review': {'reviewer': 'Test', 'date': '2026-10-15', 'rationale': 'Synthetic'},
        'references': [{'document_sha256': 'a' * 64, 'locator': '#root'}], 'ai_assisted': True,
        'externally_verified': False}
    bundle['definitions'] = [definition]
    with pytest.raises(ValueError, match='permission'):
        public_export(bundle)
    definition['permission_evidence'] = 'Synthetic author authorization'
    assert len(public_export(bundle)['definitions']) == 1
    definition['externally_verified'] = True
    with pytest.raises(ValueError, match='AI text'):
        validate(bundle)
    definition['externally_verified'] = False
    definition['references'][0]['document_sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='unregistered'):
        validate(bundle)
