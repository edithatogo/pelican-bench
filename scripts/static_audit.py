#!/usr/bin/env python3
"""Dependency-free static and repository audit for constrained environments.

This audit is deliberately narrower than Ruff, mypy, Pyright, or Vale. It provides an
executable local floor when those tools cannot be installed, while CI remains responsible
for the authoritative third-party tool runs.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    severity: str
    category: str
    path: str
    line: int
    column: int
    message: str


@dataclass(frozen=True, slots=True)
class AuditReport:
    schema_version: str
    files_scanned: int
    python_files: int
    structured_files: int
    findings: tuple[Finding, ...]

    @property
    def error_count(self) -> int:
        return sum(item.severity == "error" for item in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(item.severity == "warning" for item in self.findings)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "files_scanned": self.files_scanned,
            "python_files": self.python_files,
            "structured_files": self.structured_files,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "passed": self.passed,
            "findings": [asdict(item) for item in self.findings],
        }


SOURCE_ROOTS = ("src", "tests", "scripts", "hf", "envs")
STRUCTURED_SUFFIXES = {".json", ".jsonl", ".toml", ".yml", ".yaml"}
TEXT_SUFFIXES = {".py", ".json", ".jsonl", ".toml", ".yml", ".yaml", ".md", ".txt"}
EXCLUDED_PARTS = {".git", ".venv", "venv", "dist", "build", "artifacts", "runs", "site"}
ACTION_PIN_RE = re.compile(r"^\s*-?\s*uses:\s*([^@\s]+)@([^\s#]+)", re.MULTILINE)
HEX_40_RE = re.compile(r"^[0-9a-f]{40}$")


class DuplicateKeyError(ValueError):
    pass


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _finding(
    code: str,
    severity: str,
    category: str,
    root: Path,
    path: Path,
    message: str,
    *,
    line: int = 1,
    column: int = 1,
) -> Finding:
    return Finding(code, severity, category, _relative(root, path), line, column, message)


def _iter_files(root: Path) -> Iterable[Path]:
    for source_root in SOURCE_ROOTS:
        base = root / source_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and not (set(path.parts) & EXCLUDED_PARTS):
                yield path
    for name in (
        "pyproject.toml",
        "renovate.json",
        "codecov.yml",
        ".vale.ini",
        ".editorconfig",
    ):
        path = root / name
        if path.exists():
            yield path
    workflows = root / ".github/workflows"
    if workflows.exists():
        yield from sorted(path for path in workflows.glob("*.yml") if path.is_file())
    styles = root / ".github/styles"
    if styles.exists():
        yield from sorted(path for path in styles.rglob("*") if path.is_file())


def _text_findings(root: Path, path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    if text and not text.endswith("\n"):
        findings.append(_finding("FMT001", "error", "format", root, path, "missing final newline"))
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.rstrip(" \t") != line:
            findings.append(
                _finding(
                    "FMT002",
                    "error",
                    "format",
                    root,
                    path,
                    "trailing whitespace",
                    line=line_number,
                    column=len(line.rstrip(" \t")) + 1,
                )
            )
        indentation = line[: len(line) - len(line.lstrip(" \t"))]
        if "\t" in indentation:
            findings.append(
                _finding(
                    "FMT003",
                    "error",
                    "format",
                    root,
                    path,
                    "tab used for indentation",
                    line=line_number,
                )
            )
        if path.suffix == ".py" and len(line) > 120 and "http" not in line:
            findings.append(
                _finding(
                    "FMT004",
                    "warning",
                    "format",
                    root,
                    path,
                    f"line length is {len(line)} characters",
                    line=line_number,
                    column=121,
                )
            )
    return findings


def _call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        parts = [function.attr]
        value = function.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return ""


def _is_mutable_default(node: ast.expr | None) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {
        "list",
        "dict",
        "set",
        "defaultdict",
    }


def _function_annotation_findings(
    root: Path,
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[Finding]:
    if not _relative(root, path).startswith("src/pelicanbench/"):
        return []
    if node.name.startswith("_") and node.name not in {"__init__", "__call__"}:
        return []
    findings: list[Finding] = []
    parameters = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg is not None:
        parameters.append(node.args.vararg)
    if node.args.kwarg is not None:
        parameters.append(node.args.kwarg)
    for argument in parameters:
        if argument.arg in {"self", "cls"}:
            continue
        if argument.annotation is None:
            findings.append(
                _finding(
                    "TYP001",
                    "error",
                    "typing",
                    root,
                    path,
                    f"public callable {node.name!r} has unannotated parameter {argument.arg!r}",
                    line=argument.lineno,
                    column=argument.col_offset + 1,
                )
            )
    if node.returns is None and node.name != "__init__":
        findings.append(
            _finding(
                "TYP002",
                "error",
                "typing",
                root,
                path,
                f"public callable {node.name!r} has no return annotation",
                line=node.lineno,
                column=node.col_offset + 1,
            )
        )
    return findings


def _python_findings(root: Path, path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(text, filename=str(path), type_comments=True)
    except SyntaxError as exc:
        return [
            _finding(
                "PY001",
                "error",
                "syntax",
                root,
                path,
                exc.msg,
                line=exc.lineno or 1,
                column=exc.offset or 1,
            )
        ]

    loaded_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    exported_names: set[str] = set()
    for statement in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(statement, ast.Assign) and statement.targets:
            target = statement.targets[0]
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            target = statement.target
            value = statement.value
        if (
            isinstance(target, ast.Name)
            and target.id == "__all__"
            and isinstance(value, (ast.List, ast.Tuple))
        ):
            exported_names.update(
                item.value
                for item in value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            )

    for statement in tree.body:
        imported: list[tuple[str, int, int]] = []
        if isinstance(statement, ast.Import):
            imported.extend(
                (alias.asname or alias.name.split(".", 1)[0], statement.lineno, statement.col_offset + 1)
                for alias in statement.names
            )
        elif isinstance(statement, ast.ImportFrom) and statement.module != "__future__":
            imported.extend(
                (alias.asname or alias.name, statement.lineno, statement.col_offset + 1)
                for alias in statement.names
                if alias.name != "*"
            )
        source_line = text.splitlines()[statement.lineno - 1] if statement.lineno else ""
        for name, line, column in imported:
            if name.startswith("_") or name in loaded_names or name in exported_names:
                continue
            if "# noqa" in source_line or "# type: ignore" in source_line:
                continue
            findings.append(
                _finding(
                    "PY005",
                    "error",
                    "lint",
                    root,
                    path,
                    f"unused import {name!r}",
                    line=line,
                    column=column,
                )
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            findings.append(
                _finding(
                    "PY002",
                    "error",
                    "lint",
                    root,
                    path,
                    "wildcard import",
                    line=node.lineno,
                    column=node.col_offset + 1,
                )
            )
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(
                _finding(
                    "PY003",
                    "error",
                    "lint",
                    root,
                    path,
                    "bare except clause",
                    line=node.lineno,
                    column=node.col_offset + 1,
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(_function_annotation_findings(root, path, node))
            defaults: list[ast.expr | None] = [*node.args.defaults, *node.args.kw_defaults]
            if any(_is_mutable_default(value) for value in defaults):
                findings.append(
                    _finding(
                        "PY004",
                        "error",
                        "lint",
                        root,
                        path,
                        f"mutable default argument in {node.name!r}",
                        line=node.lineno,
                        column=node.col_offset + 1,
                    )
                )
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name in {"eval", "exec", "builtins.eval", "builtins.exec"}:
                findings.append(
                    _finding(
                        "SEC001",
                        "error",
                        "security",
                        root,
                        path,
                        f"dynamic code execution via {name}",
                        line=node.lineno,
                        column=node.col_offset + 1,
                    )
                )
            if name.startswith("subprocess.") and any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            ):
                findings.append(
                    _finding(
                        "SEC002",
                        "error",
                        "security",
                        root,
                        path,
                        "subprocess invocation uses shell=True",
                        line=node.lineno,
                        column=node.col_offset + 1,
                    )
                )
            if name in {"datetime.utcnow", "datetime.datetime.utcnow"}:
                findings.append(
                    _finding(
                        "DTZ001",
                        "error",
                        "time",
                        root,
                        path,
                        "naive UTC timestamp; use the repository time utility",
                        line=node.lineno,
                        column=node.col_offset + 1,
                    )
                )
            if name in {
                "urllib.request.urlopen",
                "requests.get",
                "requests.post",
                "httpx.get",
                "httpx.post",
            } and not any(keyword.arg == "timeout" for keyword in node.keywords):
                findings.append(
                    _finding(
                        "NET001",
                        "error",
                        "reliability",
                        root,
                        path,
                        f"network call {name} has no explicit timeout",
                        line=node.lineno,
                        column=node.col_offset + 1,
                    )
                )
    return findings


def _structured_findings(root: Path, path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        if path.suffix == ".json":
            json.loads(text, object_pairs_hook=_json_object)
        elif path.suffix == ".jsonl":
            for line_number, line in enumerate(text.splitlines(), 1):
                if line.strip():
                    try:
                        json.loads(line, object_pairs_hook=_json_object)
                    except (json.JSONDecodeError, DuplicateKeyError) as exc:
                        findings.append(
                            _finding(
                                "DATA002",
                                "error",
                                "structured-data",
                                root,
                                path,
                                str(exc),
                                line=line_number,
                            )
                        )
        elif path.suffix == ".toml":
            tomllib.loads(text)
        elif path.suffix in {".yml", ".yaml"}:
            try:
                import yaml  # type: ignore[import-untyped]
            except ModuleNotFoundError:
                if "\t" in text:
                    raise ValueError("YAML contains a tab")
            else:
                yaml.safe_load(text)
    except (json.JSONDecodeError, DuplicateKeyError, tomllib.TOMLDecodeError, ValueError) as exc:
        findings.append(
            _finding(
                "DATA001",
                "error",
                "structured-data",
                root,
                path,
                str(exc),
            )
        )
    except Exception as exc:  # YAML parser error type is optional at runtime.
        findings.append(
            _finding(
                "DATA001",
                "error",
                "structured-data",
                root,
                path,
                f"{type(exc).__name__}: {exc}",
            )
        )
    return findings


def _workflow_findings(root: Path, path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in ACTION_PIN_RE.finditer(text):
        action, revision = match.groups()
        if action.startswith("./"):
            continue
        if not HEX_40_RE.fullmatch(revision):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(
                _finding(
                    "CICD001",
                    "error",
                    "supply-chain",
                    root,
                    path,
                    f"GitHub Action {action!r} is not pinned to a 40-character commit SHA",
                    line=line,
                )
            )
    return findings


def _configuration_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    required = {
        "codecov.yml": "Codecov configuration",
        "renovate.json": "Renovate configuration",
        ".vale.ini": "Vale configuration",
        ".github/workflows/quality.yml": "quality workflow",
        ".github/workflows/test-taxonomy.yml": "test-taxonomy workflow",
        ".github/workflows/mutation.yml": "mutation workflow",
    }
    for relative, description in required.items():
        path = root / relative
        if not path.exists():
            findings.append(
                Finding(
                    "CFG001",
                    "error",
                    "configuration",
                    relative,
                    1,
                    1,
                    f"missing required {description}",
                )
            )
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        value = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        threshold = float(value.get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under", 0))
        if threshold < 90:
            findings.append(
                _finding(
                    "CFG002",
                    "error",
                    "coverage",
                    root,
                    pyproject,
                    f"coverage fail_under is {threshold:g}; expected at least 90",
                )
            )
        mypy = value.get("tool", {}).get("mypy", {})
        if mypy.get("strict") is not True:
            findings.append(_finding("CFG003", "error", "typing", root, pyproject, "mypy strict mode is disabled"))
        pyright = value.get("tool", {}).get("pyright", {})
        if pyright.get("typeCheckingMode") != "strict":
            findings.append(_finding("CFG004", "error", "typing", root, pyproject, "Pyright strict mode is disabled"))
    return findings


def audit_repository(root: Path) -> AuditReport:
    root = root.resolve()
    findings: list[Finding] = []
    files = tuple(dict.fromkeys(_iter_files(root)))
    python_count = 0
    structured_count = 0
    for path in files:
        if path.suffix not in TEXT_SUFFIXES and path.name not in {".vale.ini", ".editorconfig"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            findings.append(_finding("ENC001", "error", "encoding", root, path, str(exc)))
            continue
        findings.extend(_text_findings(root, path, text))
        if path.suffix == ".py":
            python_count += 1
            findings.extend(_python_findings(root, path, text))
        if path.suffix in STRUCTURED_SUFFIXES:
            structured_count += 1
            findings.extend(_structured_findings(root, path, text))
        if path.parent == root / ".github/workflows" and path.suffix in {".yml", ".yaml"}:
            findings.extend(_workflow_findings(root, path, text))
    findings.extend(_configuration_findings(root))
    findings.sort(key=lambda item: (item.path, item.line, item.column, item.code))
    return AuditReport("1.0.0", len(files), python_count, structured_count, tuple(findings))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/static-audit.json")
    parser.add_argument("--fail-on-warnings", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = audit_repository(root)
    payload = report.as_dict()
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for finding in report.findings:
        print(
            f"{finding.severity.upper()} {finding.code} "
            f"{finding.path}:{finding.line}:{finding.column} {finding.message}"
        )
    print(
        f"Static audit: {report.files_scanned} files, {report.error_count} errors, "
        f"{report.warning_count} warnings."
    )
    failed = not report.passed or (args.fail_on_warnings and report.warning_count > 0)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
