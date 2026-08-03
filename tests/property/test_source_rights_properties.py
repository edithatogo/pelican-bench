from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from pelicanbench.source_rights import audit_sourced_artifacts

pytestmark = pytest.mark.property


@pytest.mark.skipif(
    importlib.util.find_spec("hypothesis") is None,
    reason="Hypothesis is a mandatory CI dependency",
)
def test_arbitrary_unregistered_sources_fail_closed(tmp_path: Path) -> None:
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=50, derandomize=True)
    @given(
        source_id=st.text(min_size=1, max_size=64),
        rights_status=st.text(max_size=64).filter(
            lambda value: not value.startswith("project-original")
        ),
    )
    def check(source_id: str, rights_status: str) -> None:
        project = tmp_path / "project"
        fixtures = project / "data/fixtures"
        sources = project / "data/sources"
        fixtures.mkdir(parents=True, exist_ok=True)
        sources.mkdir(parents=True, exist_ok=True)
        (sources / "rights-ledger.json").write_text(
            '{"schema_version":"1.0.0","decisions":[]}\n', encoding="utf-8"
        )
        (fixtures / "case.jsonl").write_text(
            json.dumps({"source_id": source_id, "rights_status": rights_status}) + "\n",
            encoding="utf-8",
        )
        report = audit_sourced_artifacts(project)
        assert not report.passed
        assert {finding.code for finding in report.findings} == {"unregistered-source"}

    check()
