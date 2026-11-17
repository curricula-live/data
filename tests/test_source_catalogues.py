"""Source admission and draft identity expansion regression tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cso35_source_catalog as cso
import historical_v1_catalog as historical
import propose_historical_concepts as proposer
import source_coverage_search as lookup
import source_topic_paths as topic_paths


class Cso35Tests(unittest.TestCase):
    def test_committed_source_integrity_and_predicate_boundaries(self):
        manifest = json.loads((cso.DEST / "manifest.json").read_text())
        archive = cso.DEST / "CSO.3.5.nt.zip"
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), cso.SHA)
        self.assertEqual(manifest["topic_count"], 14636)
        self.assertEqual(manifest["triple_count"], 166518)
        self.assertEqual(manifest["uri_relation_count"], 151882)
        self.assertEqual(len(manifest["predicate_counts"]), 8)
        self.assertFalse(manifest["cross_source_identity_approved"])
        self.assertFalse(manifest["curriculum_prerequisites_inferred"])
        self.assertEqual(cso.search("machine learning")["results"][0]["label"], "machine learning")

    def test_rejects_tampered_source_and_archive_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "input.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("CSO.3.5.nt", "<https://cso.kmi.open.ac.uk/topics/a> <http://www.w3.org/2000/01/rdf-schema#label> \"a\"@en .\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                list(cso.rows(archive))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(len(list(cso.rows(archive, digest))), 1)
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../CSO.3.5.nt", "incorrect")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "exactly one CSO.3.5.nt"):
                list(cso.rows(archive, digest))


class HistoricalTests(unittest.TestCase):
    def test_identity_proposals_are_deterministic_and_do_not_import_edges(self):
        original = [{"id": "existing-a", "slug": "array", "label": "Array"}]
        terms = [
            {"source_uri": "http://example.test/v1/array", "label": "Array"},
            {"source_uri": "http://example.test/v1/tcp", "label": "TCP"},
        ]
        rows, decisions, added = proposer.build(original, terms)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["label"], "TCP")
        self.assertEqual({d["decision"] for d in decisions},
                         {"exact_label_candidate", "proposed_concept_on_branch"})
        self.assertTrue(all(x["statement_imported"] is False for x in decisions))
        rows_again, decisions_again, added_again = proposer.build(rows, terms)
        self.assertEqual(rows, rows_again)
        self.assertEqual(added_again, [])
        self.assertEqual(len(decisions_again), len(decisions))

    def test_historical_source_is_archived_and_unchanged(self):
        m = json.loads((historical.DEST / "manifest.json").read_text())
        self.assertEqual(m["topic_count"], 2001)
        self.assertEqual(m["uri_relation_count"], 2081)
        self.assertEqual(m["predicate_counts"]["broaderTopic"], 2065)
        self.assertFalse(m["independent_scientific_approval"])
        self.assertFalse(m["cross_source_identity_approved"])
        self.assertEqual(len(proposer.load(proposer.LEDGER)), 2001)

    def test_source_hierarchy_witnesses_are_not_subtype_inferences(self):
        result = topic_paths.paths("cso", "computer science", depth=2, limit=5)
        self.assertEqual(result["predicate"], topic_paths.CSO)
        self.assertTrue(result["paths"])
        self.assertFalse(result["semantic_subtype_inferred"])
        self.assertFalse(result["prerequisite_inferred"])
        self.assertFalse(result["cross_source_identity_inferred"])
        for item in result["paths"]:
            self.assertEqual(len(item["premise_witnesses"]), item["hop_count"])
            self.assertEqual(item["status"], "source_recorded_path_not_logical_entailment")
            for edge in item["premise_witnesses"]:
                self.assertEqual(edge["predicate"], topic_paths.CSO)
        legacy = topic_paths.paths("historical-v1", "Computer science", depth=2, limit=5)
        self.assertEqual(legacy["predicate"], "broaderTopic")
        self.assertFalse(legacy["semantic_subtype_inferred"])
        with self.assertRaisesRegex(ValueError, "invalid source"):
            topic_paths.paths("unverified-source", "Computer science")

    def test_search_distinguishes_canonical_and_source_only(self):
        binary_tree = lookup.search("binary tree")
        self.assertEqual(binary_tree["lookup_status"], "exact")
        self.assertTrue(binary_tree["canonical_exact"])  # proposed concept exists on branch
        tcp = lookup.search("tcp")
        self.assertEqual(tcp["lookup_status"], "exact")
        self.assertTrue(any(result["source"] == "cso@3.5" for result in tcp["results"]))
        self.assertFalse(tcp["source_hits_are_canonical"])
        self.assertFalse(tcp["inference_from_source_candidates_allowed"])


if __name__ == "__main__":
    unittest.main()
