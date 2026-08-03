from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.source_rights import audit_sourced_artifacts

DECISIONS_EMPTY = '{"schema_version": "1.0.0", "decisions": []}\n'


def _write_ledger(project: Path, payload: str = DECISIONS_EMPTY) -> None:
    sources = project / "data/sources"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "rights-ledger.json").write_text(payload, encoding="utf-8")


def test_committed_sourced_artifacts_are_rights_covered(root: Path) -> None:
    report = audit_sourced_artifacts(root)
    assert report.passed
    assert report.artifact_count > 0
    # The derived empirical panel and historical fixtures are covered by ledger
    # decisions or project-original declarations.
    assert report.findings == ()


def test_unregistered_source_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    fixtures = project / "data/fixtures"
    fixtures.mkdir(parents=True)
    _write_ledger(project)
    (fixtures / "corpus.jsonl").write_text(
        json.dumps({"source_id": "mystery-blog", "title": "A foreign post"}) + "\n",
        encoding="utf-8",
    )
    report = audit_sourced_artifacts(project)
    assert not report.passed
    assert any(
        item.code == "unregistered-source" and "mystery-blog" in item.message
        for item in report.findings
    )


def test_project_original_declaration_is_sufficient(tmp_path: Path) -> None:
    project = tmp_path / "project"
    fixtures = project / "data/fixtures"
    fixtures.mkdir(parents=True)
    _write_ledger(project)
    (fixtures / "original.jsonl").write_text(
        json.dumps({"source_id": "fixture-007", "rights_status": "project-original-fixture"})
        + "\n",
        encoding="utf-8",
    )
    report = audit_sourced_artifacts(project)
    assert report.passed
    assert report.artifact_count == 1


def test_ledger_decision_covers_source(tmp_path: Path) -> None:
    project = tmp_path / "project"
    fixtures = project / "data/fixtures"
    fixtures.mkdir(parents=True)
    _write_ledger(
        project,
        json.dumps(
            {
                "schema_version": "1.0.0",
                "decisions": [
                    {
                        "source_id": "granted-source",
                        "decision": "redistributable",
                        "rationale": "Permission granted.",
                        "artifact_class": "text",
                    }
                ],
            }
        )
        + "\n",
    )
    (fixtures / "x.jsonl").write_text(
        json.dumps({"source_id": "granted-source", "title": "Permitted"}) + "\n",
        encoding="utf-8",
    )
    assert audit_sourced_artifacts(project).passed


def test_missing_source_id_is_an_error(tmp_path: Path) -> None:
    project = tmp_path / "project"
    fixtures = project / "data/fixtures"
    fixtures.mkdir(parents=True)
    _write_ledger(project)
    (fixtures / "broken.jsonl").write_text('{"title": "no source"}\n', encoding="utf-8")
    report = audit_sourced_artifacts(project)
    assert not report.passed
    assert any(item.code == "missing-source-id" for item in report.findings)


def test_malformed_ledger_and_records_fail_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "data/fixtures").mkdir(parents=True)
    _write_ledger(project, '{"schema_version": "1.0.0"}\n')
    with pytest.raises(ValueError, match="decisions list"):
        audit_sourced_artifacts(project)

    _write_ledger(project)
    (project / "data/fixtures" / "bad.jsonl").write_text('["not", "an", "object"]\n')
    with pytest.raises(ValueError, match="JSON object"):
        audit_sourced_artifacts(project)


@pytest.mark.parametrize("schema_version", [None, "0.9.0", "2.0.0"])
def test_unsupported_ledger_schema_requires_explicit_migration(
    tmp_path: Path, schema_version: str | None
) -> None:
    project = tmp_path / "project"
    (project / "data/fixtures").mkdir(parents=True)
    ledger: dict[str, object] = {"decisions": []}
    if schema_version is not None:
        ledger["schema_version"] = schema_version
    _write_ledger(project, json.dumps(ledger) + "\n")

    with pytest.raises(ValueError, match="unsupported rights-ledger schema"):
        audit_sourced_artifacts(project)


def test_blank_lines_are_ignored(tmp_path: Path) -> None:
    project = tmp_path / "project"
    fixtures = project / "data/fixtures"
    fixtures.mkdir(parents=True)
    _write_ledger(project)
    (fixtures / "blank.jsonl").write_text(
        json.dumps({"source_id": "fixture-a", "rights_status": "project-original"})
        + "\n\n"
        + json.dumps({"source_id": "fixture-b", "rights_status": "project-original-fixture"})
        + "\n",
        encoding="utf-8",
    )
    report = audit_sourced_artifacts(project)
    assert report.passed
    assert report.artifact_count == 2
