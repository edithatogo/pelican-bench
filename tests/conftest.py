from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.taskgen import heritage_task, load_grammar


@pytest.fixture(scope="session")
def root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def grammar(root: Path):
    return load_grammar(root / "benchmark/tasks/grammar.json")


@pytest.fixture(scope="session")
def heritage():
    return heritage_task()


@pytest.fixture(scope="session")
def valid_svg(root: Path) -> str:
    return (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def broken_svg(root: Path) -> str:
    return (root / "benchmark/fixtures/svg/pelican-bicycle-broken.svg").read_text(encoding="utf-8")


CATEGORY_MARKERS = {
    "unit",
    "integration",
    "e2e",
    "property",
    "mutation",
    "edge",
    "dst",
    "contract",
    "metamorphic",
    "agent",
    "autonomous",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Ensure every test belongs to at least one explicit quality taxonomy lane."""

    for item in items:
        present = {name for name in CATEGORY_MARKERS if item.get_closest_marker(name) is not None}
        if not present:
            item.add_marker(pytest.mark.unit)
