from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from pelicanbench.workgraph import build_issue_manifest

pytestmark = pytest.mark.integration


def _packages(manifest: dict[str, object]) -> list[dict[str, object]]:
    tracks = manifest["tracks"]
    assert isinstance(tracks, list)
    return [
        package
        for track in tracks
        for phase in track["phases"]
        for package in phase.get("work_packages", [])
    ]


def test_nested_work_packages_are_stable_and_phase_scoped(root: Path) -> None:
    actual = json.loads((root / ".github/issues/manifest.json").read_text(encoding="utf-8"))
    expected = build_issue_manifest(
        root,
        generated_at=actual["generated_at"],
        preserve_numbers=True,
    )
    assert actual == expected
    packages = _packages(actual)
    assert packages
    assert len({package["id"] for package in packages}) == len(packages)
    for track in actual["tracks"]:
        for phase in track["phases"]:
            for package in phase.get("work_packages", []):
                assert package["phase"] == phase["phase"]
                assert package["id"].startswith(f"{track['track_id']}-{phase['phase']}-")


def test_issue_sync_apply_path_builds_three_level_hierarchy_without_network(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = runpy.run_path(str(root / "scripts/sync_github_issues.py"))
    manifest = json.loads((root / ".github/issues/manifest.json").read_text(encoding="utf-8"))
    manifest_path = tmp_path / "manifest.json"
    state_path = tmp_path / "state.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    issue_counter = iter(range(1, 10000))
    attachments: list[tuple[int, int]] = []
    labels_seen: list[str] = []

    def fake_issue(_repo: str, **_kwargs: object) -> dict[str, int]:
        number = next(issue_counter)
        return {"number": number, "id": 100000 + number}

    def fake_labels(_repo: str, tracks: list[dict[str, object]]) -> None:
        labels_seen.extend(str(track["track_id"]) for track in tracks)

    main = namespace["main"]
    main.__globals__["MANIFEST"] = manifest_path
    main.__globals__["STATE"] = state_path
    main.__globals__["run_json"] = lambda _command: {"hosts": {}}
    main.__globals__["ensure_labels"] = fake_labels
    main.__globals__["ensure_issue"] = fake_issue
    main.__globals__["attach_native_sub_issue"] = lambda _repo, parent, child: attachments.append(
        (parent, child)
    )
    monkeypatch.setattr(main.__globals__["shutil"], "which", lambda _name: "/fixture/gh")
    monkeypatch.setattr(sys, "argv", ["sync_github_issues.py", "--apply", "--repo", "x/y"])

    assert main() == 0
    synchronized = json.loads(manifest_path.read_text(encoding="utf-8"))
    packages = _packages(synchronized)
    phase_count = sum(len(track["phases"]) for track in synchronized["tracks"])
    assert labels_seen == [track["track_id"] for track in synchronized["tracks"]]
    assert all(package["issue_number"] for package in packages)
    assert len(attachments) == phase_count + len(packages)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["tracks"]["T10"]["phases"]["P2"]["work_packages"]
