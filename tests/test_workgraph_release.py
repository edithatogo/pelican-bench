from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path

from pelicanbench.conductor_docs import generated_documents
from pelicanbench.release_manifest import build_release_manifest
from pelicanbench.validation import (
    _validate_assurance,
    _validate_known_exploits,
    validate_repository,
)
from pelicanbench.workgraph import build_issue_manifest


def test_generated_conductor_views_and_issue_graph_are_current(root: Path):
    for path, expected in generated_documents(root).items():
        assert path.read_text(encoding="utf-8") == expected
    actual = json.loads((root / ".github/issues/manifest.json").read_text(encoding="utf-8"))
    expected = build_issue_manifest(
        root,
        generated_at=actual["generated_at"],
        preserve_numbers=True,
    )
    assert actual == expected
    assert len(actual["tracks"]) == 22
    assert sum(len(item["phases"]) for item in actual["tracks"]) == 88
    assert len(actual["release_blockers"]) == 5
    archived = next(item for item in actual["tracks"] if item["track_id"] == "T00")
    assert archived["path"] == "conductor/archive/t00-foundation-governance-and-conductor"
    registry = (root / "conductor/tracks.md").read_text(encoding="utf-8")
    assert "- [x] **T00:" in registry
    assert "(archive/t00-foundation-governance-and-conductor/index.md)" in registry
    assert "- [~] **T01:" in registry


def test_release_manifest_records_assurance_work_graph_and_artifacts(root: Path, tmp_path: Path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("pelican\n", encoding="utf-8")
    manifest = build_release_manifest(
        root,
        profile="v0.2-alpha",
        tag="not-a-real-tag",
        artifacts=(artifact,),
    )
    assert manifest["release"]["ready"] is True
    assert manifest["release"]["tag_points_at_head"] is False
    assert manifest["work_graph"]["work_item_count"] == 115
    assert manifest["benchmark"]["task_count"] == 33
    assert manifest["artifacts"][0]["sha256"].startswith("sha256:")
    assert len(manifest["key_files"]) >= 6


def test_sbom_contains_source_and_dependency_relationships(root: Path):
    namespace = runpy.run_path(str(root / "scripts/generate_sbom.py"))
    document = namespace["build_sbom"]()
    package_ids = {item["SPDXID"] for item in document["packages"]}
    assert "SPDXRef-Package-pelicanbench" in package_ids
    assert "SPDXRef-Package-cairosvg" in package_ids
    assert document["files"]
    dependency_relationships = [
        item for item in document["relationships"] if item["relationshipType"] == "DEPENDS_ON"
    ]
    assert dependency_relationships
    assert all(
        item["spdxElementId"] == "SPDXRef-Package-pelicanbench" for item in dependency_relationships
    )


def _copy_repository(root: Path, destination: Path) -> Path:
    return Path(
        shutil.copytree(
            root,
            destination,
            ignore=shutil.ignore_patterns(
                ".git",
                "artifacts",
                "runs",
                "__pycache__",
                ".pytest_cache",
                ".coverage",
                "coverage.xml",
            ),
        )
    )


def test_validation_rejects_stale_generated_views(root: Path, tmp_path: Path):
    project = _copy_repository(root, tmp_path / "repo")
    status = project / "conductor/status.md"
    status.write_text(status.read_text(encoding="utf-8") + "stale\n", encoding="utf-8")
    manifest_path = project / ".github/issues/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tracks"][0]["title"] = "stale"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    codes = {item.code for item in validate_repository(project)}
    assert "stale-conductor-view" in codes
    assert "stale-issue-manifest" in codes


def test_validation_rejects_inconsistent_blockers_and_broken_exploit_refs(
    root: Path, tmp_path: Path
):
    project = _copy_repository(root, tmp_path / "repo")
    blockers_path = project / "conductor/release-blockers.json"
    blockers = json.loads(blockers_path.read_text(encoding="utf-8"))
    blockers["blockers"][0]["status"] = "complete"
    blockers_path.write_text(json.dumps(blockers), encoding="utf-8")
    assurance_codes = {item.code for item in _validate_assurance(project)}
    assert "inconsistent-blocker-status" in assurance_codes

    registry_path = project / "benchmark/scorer-challenges/known-exploits.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["exploits"][0]["regression_tests"] = ["tests/test_svg_scoring.py::test_does_not_exist"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    exploit_codes = {item.code for item in _validate_known_exploits(project)}
    assert "missing-exploit-test" in exploit_codes


def test_validation_requires_immutable_workflow_action_pins(root: Path, tmp_path: Path):
    project = _copy_repository(root, tmp_path / "repo")
    workflow = project / ".github/workflows/ci.yml"
    text = workflow.read_text(encoding="utf-8")
    text = text.replace(
        "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd",
        "actions/checkout@v6",
        1,
    )
    workflow.write_text(text, encoding="utf-8")
    codes = {item.code for item in validate_repository(project)}
    assert "unpinned-workflow-action" in codes
