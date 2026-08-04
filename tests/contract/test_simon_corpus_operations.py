from __future__ import annotations

import json
from pathlib import Path


def test_simon_corpus_operations_preserve_rights_and_custody(root: Path) -> None:
    policy = json.loads(
        (root / "benchmark/evidence/snapshots/simon-corpus-operations.json").read_text(
            encoding="utf-8"
        )
    )

    assert policy["schema_version"] == "1.0.0"
    assert policy["ownership"] == {
        "accountable_role": "benchmark-steward",
        "backup_role": None,
        "corpus_custodian": "benchmark-steward",
        "external_source_reviewer": "unassigned",
    }
    assert policy["incident"]["severity"] == "P0-critical"
    assert policy["incident"]["response"][:3] == [
        "freeze-corpus-publication",
        "quarantine-affected-content",
        "preserve-metadata-fixity-and-receipts",
    ]
    assert "obtain-accountable-source-review" in policy["incident"]["response"]
    assert policy["archive"]["retention"] == "permanent"
    assert policy["archive"]["restricted_content_public"] is False
