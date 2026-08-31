"""The local archive is deterministic preparation, never publication authority."""

import hashlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "preview_bundle", ROOT / "scripts/build_t14_workflow_preview_bundle.py"
)
assert SPEC and SPEC.loader
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


@pytest.fixture
def package(tmp_path):
    return Path(shutil.copytree(bundle.PACKAGE, tmp_path / "package"))


def test_reproducible_exact_members_and_metadata(package, tmp_path):
    first = bundle.build(package)
    (package / "index.html").chmod(0o600)
    second = bundle.build(package)
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == list(bundle.ALLOWLIST)
        assert archive.comment == b""
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert info.external_attr == 0o100644 << 16
            assert info.extra == info.comment == b""
            assert archive.read(info) == (package / info.filename).read_bytes()
    output = tmp_path / "preview.zip"
    bundle.write(output, package)
    assert output.read_bytes() == first
    with pytest.raises(FileExistsError):
        bundle.write(output, package)
    assert output.read_bytes() == first


@pytest.mark.parametrize("attack", ["extra", "missing", "changed", "directory", "oversize"])
def test_package_rejection_leaves_no_archive(package, tmp_path, attack):
    member = package / "style.css"
    if attack == "extra":
        (package / ".hidden").write_text("extra")
    elif attack == "missing":
        member.unlink()
    elif attack == "changed":
        member.write_bytes(b"x" * member.stat().st_size)
    elif attack == "directory":
        member.unlink()
        member.mkdir()
    else:
        member.write_bytes(b"x" * 100_000)
    output = tmp_path / "preview.zip"
    with pytest.raises(ValueError):
        bundle.write(output, package)
    assert not output.exists()
    assert not list(tmp_path.glob(".t14-preview-*"))


@pytest.mark.parametrize("kind", ["member", "package", "manifest", "output", "parent"])
def test_symlinks_rejected(package, tmp_path, kind):
    manifest = bundle.MANIFEST
    output = tmp_path / "preview.zip"
    if kind == "member":
        (package / "style.css").unlink()
        (package / "style.css").symlink_to(bundle.PACKAGE / "style.css")
    elif kind == "package":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        package = alias / "package"
    elif kind == "manifest":
        manifest = tmp_path / "manifest.json"
        manifest.symlink_to(bundle.MANIFEST)
    elif kind == "output":
        output.symlink_to(tmp_path / "absent")
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        output = alias / "preview.zip"
    with pytest.raises(ValueError, match="symlink"):
        bundle.write(output, package, manifest)
    assert not (tmp_path / "absent").exists()


def test_manifest_exact_hash_binding(package, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(bundle.MANIFEST.read_bytes() + b" ")
    assert hashlib.sha256(bundle.MANIFEST.read_bytes()).hexdigest() == bundle.MANIFEST_SHA256
    with pytest.raises(ValueError, match="reviewed manifest"):
        bundle.build(package, manifest)


def test_output_must_remain_outside_package(package):
    with pytest.raises(ValueError, match="outside"):
        bundle.write(package / "preview.zip", package)


def test_failed_final_link_cleans_staging(package, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("simulated link failure")

    monkeypatch.setattr(bundle.os, "link", fail)
    output = tmp_path / "preview.zip"
    with pytest.raises(OSError, match="simulated"):
        bundle.write(output, package)
    assert not output.exists()
    assert not list(tmp_path.glob(".t14-preview-*"))


def test_fifo_and_parent_traversal_rejected(package, tmp_path):
    member = package / "style.css"
    member.unlink()
    os.mkfifo(member)
    with pytest.raises(ValueError, match="nonregular"):
        bundle.build(package)
    with pytest.raises(ValueError, match="traversal"):
        bundle.write(tmp_path / "package/../preview.zip", package)


def test_archived_bytes_are_validated_snapshot(package, monkeypatch):
    original = bundle.read_bounded
    calls = []

    def read_then_mutate(path, limit):
        data = original(path, limit)
        if path.parent == package:
            calls.append(path.name)
            path.write_bytes(b"changed after snapshot")
        return data

    expected = bundle.build(package)
    monkeypatch.setattr(bundle, "read_bounded", read_then_mutate)
    assert bundle.build(package) == expected
    assert calls == list(bundle.ALLOWLIST)


def test_target_created_during_staging_not_overwritten(package, tmp_path, monkeypatch):
    original = bundle.os.link
    output = tmp_path / "preview.zip"

    def concurrent_target(*args, **kwargs):
        output.write_bytes(b"preserved")
        return original(*args, **kwargs)

    monkeypatch.setattr(bundle.os, "link", concurrent_target)
    with pytest.raises(FileExistsError):
        bundle.write(output, package)
    assert output.read_bytes() == b"preserved"
    assert not list(tmp_path.glob(".t14-preview-*"))


def test_cli_is_local_create_only(tmp_path):
    output = tmp_path / "preview.zip"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_t14_workflow_preview_bundle.py"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == bundle.build()
