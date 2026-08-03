from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_static_audit() -> ModuleType:
    path = ROOT / "scripts/static_audit.py"
    spec = importlib.util.spec_from_file_location("pelicanbench_static_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load static_audit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.edge
def test_static_audit_detects_shadowed_module_and_class_definitions(tmp_path: Path) -> None:
    module = _load_static_audit()
    source = """\
def duplicate() -> int:
    return 1


def duplicate() -> int:
    return 2


class Example:
    def method(self) -> int:
        return 1

    def method(self) -> int:
        return 2
"""
    path = tmp_path / "src/pelicanbench/duplicate.py"
    path.parent.mkdir(parents=True)
    findings = module._python_findings(tmp_path, path, source)
    duplicates = [item for item in findings if item.code == "PY006"]
    assert len(duplicates) == 2
    assert {item.line for item in duplicates} == {5, 13}


@pytest.mark.edge
def test_static_audit_allows_overloads_and_property_accessors(tmp_path: Path) -> None:
    module = _load_static_audit()
    source = """\
from typing import overload


@overload
def convert(value: int) -> str: ...


@overload
def convert(value: str) -> str: ...


def convert(value: object) -> str:
    return str(value)


class Example:
    @property
    def value(self) -> int:
        return 1

    @value.setter
    def value(self, new_value: int) -> None:
        _ = new_value
"""
    path = tmp_path / "src/pelicanbench/allowed.py"
    path.parent.mkdir(parents=True)
    findings = module._python_findings(tmp_path, path, source)
    assert not [item for item in findings if item.code == "PY006"]


@pytest.mark.edge
def test_static_audit_detects_duplicate_import_bindings(tmp_path: Path) -> None:
    module = _load_static_audit()
    source = """\
from first import value
from second import value
"""
    path = tmp_path / "src/pelicanbench/duplicate_import.py"
    path.parent.mkdir(parents=True)
    findings = module._python_findings(tmp_path, path, source)
    duplicates = [item for item in findings if item.code == "PY007"]
    assert len(duplicates) == 1
    assert duplicates[0].line == 2


@pytest.mark.edge
def test_static_audit_allows_distinct_import_aliases(tmp_path: Path) -> None:
    module = _load_static_audit()
    source = """\
from first import value as first_value
from second import value as second_value

__all__ = ["first_value", "second_value"]
"""
    path = tmp_path / "src/pelicanbench/distinct_imports.py"
    path.parent.mkdir(parents=True)
    findings = module._python_findings(tmp_path, path, source)
    assert not [item for item in findings if item.code == "PY007"]


@pytest.mark.edge
def test_static_audit_allows_multiple_submodule_imports(tmp_path: Path) -> None:
    module = _load_static_audit()
    source = """\
import urllib.error
import urllib.request

__all__ = ["urllib"]
"""
    path = tmp_path / "src/pelicanbench/submodules.py"
    path.parent.mkdir(parents=True)
    findings = module._python_findings(tmp_path, path, source)
    assert not [item for item in findings if item.code == "PY007"]
