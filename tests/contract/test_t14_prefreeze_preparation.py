from __future__ import annotations

import importlib.util
from pathlib import Path


def test_prefreeze_preparation_is_bound_and_fail_closed() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_prefreeze_preparation.py"
    spec = importlib.util.spec_from_file_location("validate_t14_prefreeze_preparation", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
