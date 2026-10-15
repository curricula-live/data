"""Deterministic, credential-free evidence for a strict staging PostgreSQL parity run.

This does NOT prove the database is staging: an operator must independently
verify the isolated PostgreSQL destination before providing its expected name
and role. Evidence cannot be created without an actual successful strict
legacy + v2 comparison in the caller.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CORPUS_PATHS = (
    "knowledge/concepts.jsonl",
    "knowledge/predicates.jsonl",
    "knowledge/statements.jsonl",
    "knowledge/definitions.jsonl",
    "migration/legacy-v1/manifest.json",
    "migration/legacy-v1/concept-identities.jsonl",
    "migration/legacy-v1/statement-uuids.txt",
)
_SHA = re.compile(r"^[0-9a-f]{40}$")


def corpus_sha256(root: Path) -> str:
    """Hash both file names and exact bytes (including line endings) in order."""
    digest = hashlib.sha256()
    for relative in CORPUS_PATHS:
        data = (root / relative).read_bytes()
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def verified_git_head(root: Path, expected_sha: str) -> str:
    """Refuse an unpinned revision or modified/untracked evidence inputs."""
    if not _SHA.fullmatch(expected_sha):
        raise ValueError("expected Git commit must be a full lowercase 40-character SHA")
    actual = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    if actual != expected_sha:
        raise ValueError("checked-out Git commit differs from expected release commit")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *CORPUS_PATHS], cwd=root,
        check=True, capture_output=True, text=True,
    ).stdout
    if status.strip():
        raise ValueError("canonical corpus or migration ledgers have uncommitted changes")
    return actual


def check_read_only_target(cursor: Any, expected_database: str, expected_role: str) -> dict[str, str]:
    """Check the current PostgreSQL target within the read-only transaction."""
    if not expected_database or not expected_role:
        raise ValueError("expected database and role must both be provided")
    cursor.execute(
        "select current_database(), current_user, current_setting('transaction_read_only')"
    )
    database, role, transaction_read_only = cursor.fetchone()
    if transaction_read_only != "on":
        raise ValueError("PostgreSQL parity transaction is not read-only")
    if (database, role) != (expected_database, expected_role):
        raise ValueError("PostgreSQL database/role does not match the expected staging target")
    return {"database": database, "role": role}


def build_evidence(
    *, root: Path, git_commit: str, target: dict[str, str],
    result: dict[str, Any], verified_at: datetime | None = None,
) -> dict[str, Any]:
    """Create an auditable, non-secret certificate only for complete v2 parity."""
    if result.get("v2_runtime_parity") != "verified":
        raise ValueError("full v2 runtime parity is required for release evidence")
    if not _SHA.fullmatch(git_commit):
        raise ValueError("release commit must be a full SHA")
    if not target.get("database") or not target.get("role"):
        raise ValueError("database and role verification are required")
    moment = verified_at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("verification time must be timezone-aware")
    return {
        "format": "curricula-staging-parity-evidence@1",
        "result": "verified",
        "verified_at_utc": moment.astimezone(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "corpus_sha256": corpus_sha256(root),
        "postgresql_target": {"database": target["database"], "role": target["role"]},
        "counts": {key: value for key, value in sorted(result.items())
                   if isinstance(value, int) and not isinstance(value, bool)},
        "v2_runtime_parity": "verified",
        "scope": "read-only staging inspection; not deployment or migration approval",
    }


def write_evidence_exclusive(path: Path, evidence: dict[str, Any]) -> None:
    """Never overwrite pre-existing attestations; create file with 0600 permissions."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(evidence, out, indent=2, sort_keys=True)
            out.write("\n")
    except BaseException:
        # Avoid leaving a partial certificate that could be mistaken for success.
        path.unlink(missing_ok=True)
        raise
