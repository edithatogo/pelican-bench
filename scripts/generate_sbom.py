#!/usr/bin/env python3
"""Generate a deterministic SPDX 2.3 source and reference-environment SBOM."""

from __future__ import annotations

import argparse
import json
import os
import re
import tomllib
from pathlib import Path
from typing import Any

from pelicanbench.io import file_hash
from pelicanbench.timeutil import utc_now_iso

ROOT = Path(__file__).resolve().parents[1]
INCLUDED_SUFFIXES = {
    ".py",
    ".rs",
    ".mojo",
    ".json",
    ".jsonl",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
    ".sh",
    ".tex",
    ".ttl",
}
NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
CONSTRAINT_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$")


def _normalise_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _spdx_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9.-]+", "-", value).strip("-.")
    return token or "unnamed"


def _direct_dependencies(pyproject: dict[str, Any]) -> set[str]:
    project = pyproject.get("project", {})
    values = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        values.extend(group)
    names: set[str] = set()
    for requirement in map(str, values):
        match = NAME_RE.match(requirement)
        if match:
            names.add(_normalise_name(match.group(1)))
    return names


def _reference_environment(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = CONSTRAINT_RE.fullmatch(stripped)
        if match:
            versions[_normalise_name(match.group(1))] = match.group(2)
    return versions


def _source_files() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or ".git" in path.parts
            or "artifacts" in path.parts
            or "runs" in path.parts
            or "__pycache__" in path.parts
            or path.suffix not in INCLUDED_SUFFIXES
        ):
            continue
        relative = path.relative_to(ROOT).as_posix()
        records.append(
            {
                "SPDXID": "SPDXRef-File-" + _spdx_token(relative),
                "fileName": relative,
                "checksums": [
                    {
                        "algorithm": "SHA256",
                        "checksumValue": file_hash(path).split(":", 1)[1],
                    }
                ],
                "licenseConcluded": "NOASSERTION",
            }
        )
    return records


def build_sbom() -> dict[str, Any]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    root_id = "SPDXRef-Package-pelicanbench"
    versions = _reference_environment(ROOT / "constraints/reference-environment.txt")
    direct = _direct_dependencies(pyproject)
    files = _source_files()

    packages: list[dict[str, Any]] = [
        {
            "name": str(project["name"]),
            "SPDXID": root_id,
            "versionInfo": str(project["version"]),
            "downloadLocation": "https://github.com/edithatogo/pelican-bench",
            "filesAnalyzed": True,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "primaryPackagePurpose": "APPLICATION",
            "checksums": [],
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/{project['name']}@{project['version']}",
                }
            ],
        }
    ]
    dependency_ids: dict[str, str] = {}
    for name, version in sorted(versions.items()):
        spdx_id = "SPDXRef-Package-" + _spdx_token(name)
        dependency_ids[name] = spdx_id
        packages.append(
            {
                "name": name,
                "SPDXID": spdx_id,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "primaryPackagePurpose": "LIBRARY",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{name}@{version}",
                    }
                ],
            }
        )

    relationships: list[dict[str, str]] = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": root_id,
        }
    ]
    for file_record in files:
        relationships.append(
            {
                "spdxElementId": root_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": str(file_record["SPDXID"]),
            }
        )
    for name in sorted(direct):
        dependency_id = dependency_ids.get(name)
        if dependency_id is not None:
            relationships.append(
                {
                    "spdxElementId": root_id,
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": dependency_id,
                }
            )

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "pelican-bench-source-and-reference-environment",
        "documentNamespace": (
            "https://github.com/edithatogo/pelican-bench/sbom/"
            + os.getenv("GITHUB_SHA", "working-tree")
        ),
        "creationInfo": {
            "created": utc_now_iso(),
            "creators": ["Tool: pelicanbench-generate-sbom/0.2.0"],
            "comment": (
                "Dependency versions describe constraints/reference-environment.txt; "
                "the file explicitly records packages absent from the generating environment."
            ),
        },
        "documentDescribes": [root_id],
        "packages": packages,
        "files": files,
        "relationships": relationships,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_sbom(), sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
