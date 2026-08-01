from __future__ import annotations

import json
from pathlib import Path

from pelicanbench.validation import SCHEMA_MODELS


def test_schema_snapshots_match_models(root: Path):
    for filename, model in SCHEMA_MODELS.items():
        value = json.loads((root / "benchmark/schemas" / filename).read_text())
        assert value == model.model_json_schema()
