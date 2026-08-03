"""Content-addressed release-manifest generation."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .assurance import evaluate_release_readiness
from .io import file_hash
from .timeutil import utc_now_iso

KEY_RELEASE_FILES = (
    "benchmark/assurance-case.json",
    "benchmark/tasks/v1-pilot-commitment.json",
    "benchmark/scorer-challenges/known-exploits.json",
    "conductor/release-blockers.json",
    ".github/issues/manifest.json",
    "constraints/reference-environment.txt",
)


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _artifact_record(root: Path, value: str | Path) -> dict[str, Any]:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        name = path.relative_to(root).as_posix()
    except ValueError:
        name = path.name
    return {
        "path": name,
        "sha256": file_hash(path),
        "size_bytes": path.stat().st_size,
    }


def build_release_manifest(
    root: str | Path,
    *,
    profile: str,
    tag: str | None = None,
    artifacts: Iterable[str | Path] = (),
) -> dict[str, Any]:
    project = Path(root).resolve()
    pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    package = pyproject["project"]
    issue_manifest = json.loads(
        (project / ".github/issues/manifest.json").read_text(encoding="utf-8")
    )
    task_commitment = json.loads(
        (project / "benchmark/tasks/v1-pilot-commitment.json").read_text(encoding="utf-8")
    )
    readiness = evaluate_release_readiness(project, profile=profile)
    key_files = [_artifact_record(project, relative) for relative in KEY_RELEASE_FILES]
    artifact_records = [_artifact_record(project, value) for value in artifacts]
    commit = _git(project, "rev-parse", "HEAD")
    tree = _git(project, "rev-parse", "HEAD^{tree}")
    status = _git(project, "status", "--porcelain=v1", "--untracked-files=all")
    tag_points_at_head = None
    if tag is not None and commit is not None:
        tag_commit = _git(project, "rev-list", "-n", "1", tag)
        tag_points_at_head = tag_commit == commit if tag_commit is not None else False
    phase_count = sum(len(item.get("phases", [])) for item in issue_manifest.get("tracks", []))
    return {
        "schema_version": "1.0.0",
        "generated_at": utc_now_iso(),
        "project": {
            "name": str(package["name"]),
            "version": str(package["version"]),
            "repository": "https://github.com/edithatogo/pelican-bench",
        },
        "release": {
            "profile": profile,
            "ready": readiness.ready,
            "tag": tag,
            "tag_points_at_head": tag_points_at_head,
        },
        "git": {
            "commit": commit,
            "tree": tree,
            "clean": status == "" if status is not None else None,
        },
        "benchmark": {
            "task_commitment": task_commitment.get("commitment"),
            "task_count": task_commitment.get("task_count"),
            "scenario_count": task_commitment.get("scenario_count"),
            "prompt_count": task_commitment.get("prompt_count"),
            "scorer_version": "svg-multilayer/0.2.0",
            "canonical_renderer": "cairosvg-opaque-white/0.2.0",
        },
        "work_graph": {
            "track_count": len(issue_manifest.get("tracks", [])),
            "phase_count": phase_count,
            "release_blocker_count": len(issue_manifest.get("release_blockers", [])),
            "work_item_count": (
                len(issue_manifest.get("tracks", []))
                + phase_count
                + len(issue_manifest.get("release_blockers", []))
            ),
        },
        "assurance": readiness.as_dict(),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "executable": Path(sys.executable).name,
        },
        "key_files": key_files,
        "artifacts": artifact_records,
    }
