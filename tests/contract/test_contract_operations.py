from __future__ import annotations

import json
from pathlib import Path


def test_contract_operations_preserve_rollback_and_archive_invariants(root: Path) -> None:
    policy = json.loads(
        (root / "benchmark/evidence/snapshots/contract-operations.json").read_text(encoding="utf-8")
    )

    assert policy["schema_version"] == "1.0.0"
    assert policy["ownership"] == {
        "accountable_role": "benchmark-steward",
        "archive_custodian": "benchmark-steward",
        "backup_role": None,
        "release_authority": "benchmark-steward",
    }
    assert policy["incident"]["severity"] == "P0-critical"
    assert "restore-last-known-good-contract" in policy["incident"]["breaking_change_actions"]
    assert (
        "publish-migration-and-correction-notice" in policy["incident"]["breaking_change_actions"]
    )
    assert policy["archive"]["retention"] == "permanent"
    assert policy["archive"]["silent_recalculation_permitted"] is False
