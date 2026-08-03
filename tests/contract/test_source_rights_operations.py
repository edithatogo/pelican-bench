from __future__ import annotations

import json
from pathlib import Path


def test_source_rights_operations_remain_fail_closed(root: Path) -> None:
    policy = json.loads((root / "data/sources/operations-policy.json").read_text(encoding="utf-8"))

    assert policy["schema_version"] == "1.0.0"
    assert policy["ownership"] == {
        "accountable_role": "benchmark-steward",
        "backup_role": None,
        "external_rights_reviewer": "unassigned",
        "release_authority": "benchmark-steward",
    }
    assert policy["incident"]["classification"] == "P0-critical"
    assert policy["incident"]["response"][:3] == [
        "freeze-publication",
        "quarantine-affected-artifacts",
        "preserve-fixity-and-release-records",
    ]
    assert "obtain-accountable-rights-review" in policy["incident"]["response"]
    assert policy["incident"]["external_disclosure_must_exclude_restricted_bytes"]
    assert policy["archive"]["retention"] == "permanent"
    assert policy["archive"]["silent_rewrite_permitted"] is False
