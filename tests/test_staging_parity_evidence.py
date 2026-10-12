"""Staging evidence is deterministic, bound to Git and fail-closed."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.staging_parity_evidence import (
    CORPUS_PATHS, build_evidence, check_read_only_target, corpus_sha256,
    verified_git_head, write_evidence_exclusive,
)

SHA = "a" * 40
NOW = datetime(2026, 10, 12, 2, 30, tzinfo=timezone.utc)


def corpus(tmp_path: Path) -> Path:
    for rel in CORPUS_PATHS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((rel + "\n").encode())
    return tmp_path


def test_hash_is_deterministic_and_any_input_drift_changes_it(tmp_path):
    root = corpus(tmp_path)
    digest = corpus_sha256(root)
    assert digest == corpus_sha256(root) and len(digest) == 64
    changed = root / CORPUS_PATHS[-1]
    changed.write_bytes(changed.read_bytes() + b"\n")
    assert digest != corpus_sha256(root)


def test_git_revision_must_match_and_corpus_must_be_clean(tmp_path, monkeypatch):
    root = corpus(tmp_path)
    def fake_git(command, **kwargs):
        assert kwargs["cwd"] == root
        if command[1] == "rev-parse":
            return subprocess.CompletedProcess(command, 0, SHA + "\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr("scripts.staging_parity_evidence.subprocess.run", fake_git)
    assert verified_git_head(root, SHA) == SHA
    with pytest.raises(ValueError, match="differs"):
        verified_git_head(root, "b" * 40)
    with pytest.raises(ValueError, match="full lowercase"):
        verified_git_head(root, "a" * 8)
    def dirty(command, **kwargs):
        if command[1] == "status":
            return subprocess.CompletedProcess(command, 0, " M knowledge/concepts.jsonl\n", "")
        return fake_git(command, **kwargs)
    monkeypatch.setattr("scripts.staging_parity_evidence.subprocess.run", dirty)
    with pytest.raises(ValueError, match="uncommitted changes"):
        verified_git_head(root, SHA)


class Cursor:
    def __init__(self, result):
        self.result = result
        self.sql = None

    def execute(self, query):
        self.sql = query

    def fetchone(self):
        return self.result


def test_database_name_role_and_transaction_read_only_are_all_checked():
    good = Cursor(("atlas_stage", "atlas_reader", "on"))
    assert check_read_only_target(good, "atlas_stage", "atlas_reader") == {
        "database": "atlas_stage", "role": "atlas_reader"
    }
    assert "transaction_read_only" in good.sql
    with pytest.raises(ValueError, match="not read-only"):
        check_read_only_target(Cursor(("atlas_stage", "atlas_reader", "off")),
                               "atlas_stage", "atlas_reader")
    with pytest.raises(ValueError, match="does not match"):
        check_read_only_target(Cursor(("production", "atlas_reader", "on")),
                               "atlas_stage", "atlas_reader")
    with pytest.raises(ValueError, match="does not match"):
        check_read_only_target(Cursor(("atlas_stage", "writer", "on")),
                               "atlas_stage", "atlas_reader")


def test_evidence_requires_real_v2_verified_result_and_records_no_dsn(tmp_path):
    root = corpus(tmp_path)
    counts = {"legacy_concepts": 554, "legacy_predicates": 19,
              "legacy_statements": 663, "v2_runtime_parity": "verified"}
    expected = build_evidence(root=root, git_commit=SHA,
                              target={"database": "atlas_stage", "role": "atlas_reader"},
                              result=counts, verified_at=NOW)
    assert expected["result"] == "verified"
    assert expected["git_commit"] == SHA
    assert expected["counts"]["legacy_statements"] == 663
    assert expected["v2_runtime_parity"] == "verified"
    assert expected["postgresql_target"] == {"database": "atlas_stage", "role": "atlas_reader"}
    assert "password" not in json.dumps(expected)
    assert expected["verified_at_utc"] == NOW.isoformat()
    with pytest.raises(ValueError, match="full v2"):
        build_evidence(root=root, git_commit=SHA,
                       target={"database": "atlas_stage", "role": "atlas_reader"},
                       result={"v2_runtime_parity": "schema-not-installed"})


def test_evidence_file_is_private_and_never_overwritten(tmp_path):
    destination = tmp_path / "evidence.json"
    data = {"result": "verified"}
    write_evidence_exclusive(destination, data)
    assert json.loads(destination.read_text()) == data
    assert destination.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_evidence_exclusive(destination, {"result": "fake"})
    assert json.loads(destination.read_text()) == data
