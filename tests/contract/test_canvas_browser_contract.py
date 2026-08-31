"""Network-free browser CRUD input boundary contract using a minimal fake DOM."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pelicanbench.canvas import ALLOWED_ATTRIBUTES, ALLOWED_TAGS

pytestmark = pytest.mark.contract
ROOT = Path(__file__).resolve().parents[2]


def test_browser_canvas_contract():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable; browser contract not executed")
    result = subprocess.run(
        [
            node,
            str(ROOT / "tests/contract/canvas_browser_contract.cjs"),
            str(ROOT / "web/pelican-canvas/app.js"),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CANVAS_BROWSER_CONTRACT_OK" in result.stdout


def test_browser_tag_attribute_allowlists_match_python():
    source = (ROOT / "web/pelican-canvas/app.js").read_text()
    for name, expected in (
        ("ALLOWED_TAGS", ALLOWED_TAGS),
        ("ALLOWED_ATTRIBUTES", ALLOWED_ATTRIBUTES),
    ):
        literal = source.split(f"const {name} = new Set(", 1)[1].split(");", 1)[0]
        parsed = json.loads(literal.replace("'", '"').replace(",\n]", "\n]"))
        assert set(parsed) == expected
