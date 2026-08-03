from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.source_rights import RightsAuditPolicy, audit_sourced_artifacts


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "data/fixtures").mkdir(parents=True)
    (project / "data/sources").mkdir(parents=True)
    (project / "data/sources/rights-ledger.json").write_text(
        '{"schema_version":"1.0.0","decisions":[]}\n', encoding="utf-8"
    )
    return project


@pytest.mark.edge
def test_rights_audit_rejects_oversized_ledger_and_records(tmp_path: Path) -> None:
    project = _project(tmp_path)
    ledger = project / "data/sources/rights-ledger.json"
    ledger.write_text('{"decisions":[]}' + " " * 32, encoding="utf-8")
    policy = RightsAuditPolicy(max_ledger_bytes=16)
    with pytest.raises(ValueError, match="ledger exceeds byte limit"):
        audit_sourced_artifacts(project, policy=policy)

    ledger.write_text('{"decisions":[]}\n', encoding="utf-8")
    (project / "data/fixtures/large.jsonl").write_text(
        json.dumps(
            {
                "source_id": "fixture-a",
                "rights_status": "project-original",
                "payload": "x" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="record exceeds byte limit"):
        audit_sourced_artifacts(project, policy=RightsAuditPolicy(max_record_bytes=32))


@pytest.mark.edge
def test_rights_audit_rejects_oversized_artifact_before_parsing(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "data/fixtures/large.jsonl").write_text(
        '{"source_id":"fixture-a","rights_status":"project-original"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"artifact .* exceeds byte limit"):
        audit_sourced_artifacts(project, policy=RightsAuditPolicy(max_artifact_bytes=16))


@pytest.mark.edge
def test_rights_audit_rejects_record_count_exhaustion_and_symlinks(tmp_path: Path) -> None:
    project = _project(tmp_path)
    fixture = project / "data/fixtures/records.jsonl"
    fixture.write_text(
        "\n".join(
            json.dumps({"source_id": f"fixture-{index}", "rights_status": "project-original"})
            for index in range(3)
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="record count exceeds limit"):
        audit_sourced_artifacts(project, policy=RightsAuditPolicy(max_records=2))

    fixture.unlink()
    target = tmp_path / "outside.jsonl"
    target.write_text(
        '{"source_id":"fixture-a","rights_status":"project-original"}\n', encoding="utf-8"
    )
    fixture.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic link"):
        audit_sourced_artifacts(project)


@pytest.mark.edge
@pytest.mark.parametrize(
    "field",
    ("max_ledger_bytes", "max_artifact_bytes", "max_record_bytes", "max_records"),
)
def test_rights_audit_policy_rejects_non_positive_budgets(field: str) -> None:
    values = {field: 0}
    with pytest.raises(ValueError, match=f"{field} must be positive"):
        RightsAuditPolicy(**values)
