from __future__ import annotations

import importlib.util
from pathlib import Path


def test_pending_freeze_packet_is_bound_and_has_no_gate_effect() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_pending_freeze_packet.py"
    spec = importlib.util.spec_from_file_location("validate_t14_pending_freeze_packet", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
