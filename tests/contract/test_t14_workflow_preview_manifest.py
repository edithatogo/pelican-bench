"""Exact-package receipt remains outside the preview and grants no authority."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "preview_manifest", ROOT / "scripts/build_t14_workflow_preview_manifest.py"
)
assert SPEC and SPEC.loader
manifest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest)


@pytest.fixture
def package(tmp_path):
    destination = tmp_path / "package"
    shutil.copytree(manifest.PACKAGE, destination)
    return destination


def test_current_reproducibility_and_file_hashes():
    value = manifest.build()
    assert manifest.OUTPUT.read_bytes() == manifest.encode(value)
    manifest.check()
    assert value["destination"] is None
    assert not any(value["authority_effect"].values())
    assert value["allowlist"] == ["README.md", "index.html", "style.css"]
    assert value["total_bytes"] == sum(row["bytes"] for row in value["files"])
    for row in value["files"]:
        data = (manifest.PACKAGE / row["path"]).read_bytes()
        assert row["bytes"] == len(data)
        assert row["sha256"] == hashlib.sha256(data).hexdigest()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_t14_workflow_preview_manifest.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", ["README.md", "index.html", "style.css"])
def test_changed_package_rejects_existing_receipt(package, name):
    original = manifest.build(package)
    member = package / name
    member.write_bytes(member.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="exact package"):
        manifest.validate(original, package)


@pytest.mark.parametrize(
    "change", ["extra", "missing", "directory", "member-symlink", "ancestor-symlink"]
)
def test_allowlist_and_symlinks_fail_closed(package, tmp_path, change):
    if change == "extra":
        (package / ".hidden").write_text("not allowed")
    elif change == "missing":
        (package / "style.css").unlink()
    elif change == "directory":
        (package / "style.css").unlink()
        (package / "style.css").mkdir()
    elif change == "member-symlink":
        (package / "style.css").unlink()
        (package / "style.css").symlink_to(manifest.PACKAGE / "style.css")
    else:
        link = tmp_path / "alias"
        link.symlink_to(tmp_path, target_is_directory=True)
        package = link / "package"
    with pytest.raises(ValueError):
        manifest.build(package)


def test_create_only_external_output(package, tmp_path):
    output = tmp_path / "manifest.json"
    manifest.write(output, package)
    manifest.check(output, package)
    with pytest.raises(FileExistsError):
        manifest.write(output, package)
    with pytest.raises(ValueError, match="outside public package"):
        manifest.write(package / "manifest.json", package)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        manifest.write(alias / "other.json", package)
    with pytest.raises(ValueError, match="symlink"):
        manifest.check(alias / "manifest.json", package)


@pytest.mark.parametrize(
    "attack", ["authority", "destination", "hash", "extra", "generator", "size"]
)
def test_receipt_tampering_rejected(attack):
    value = manifest.build()
    if attack == "authority":
        value["authority_effect"]["publication"] = True
    elif attack == "destination":
        value["destination"] = "unapproved-space"
    elif attack == "hash":
        value["files"][0]["sha256"] = "0" * 64
    elif attack == "generator":
        value["generator_sha256"] = "0" * 64
    elif attack == "size":
        value["files"][0]["bytes"] += 1
    else:
        value["responses"] = []
    with pytest.raises(ValueError, match="exact package"):
        manifest.validate(value)


def test_noncanonical_encoding_rejected(tmp_path):
    output = tmp_path / "manifest.json"
    output.write_text(json.dumps(manifest.build()))
    with pytest.raises(ValueError, match="noncanonical"):
        manifest.check(output)
