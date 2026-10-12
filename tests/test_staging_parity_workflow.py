"""Fail-closed invariants for the manually dispatched parity evidence workflow."""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/staging-parity-evidence.yml"


def test_manual_only_staging_parity_workflow_never_uses_production_runner():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in content
    assert "\n  push:" not in content
    assert "\n  pull_request:" not in content
    assert "environment: knowledge-staging" in content
    assert "refs/heads/dev" in content
    assert "READ_ONLY_STAGING_PARITY" in content
    assert "secrets.STAGING_PARITY_DATABASE_URL" in content
    assert "--require-v2" in content
    assert "--expected-database" in content
    assert "--expected-role" in content
    assert "--expected-git-sha \"$GITHUB_SHA\"" in content
    assert "--evidence-out" in content
    assert "actions/upload-artifact@" in content
    assert "persist-credentials: false" in content
    assert "python scripts/publish.py apply" not in content
    assert "psql " not in content
