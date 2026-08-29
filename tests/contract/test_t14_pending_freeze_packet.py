from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def test_pending_freeze_packet_binds_local_harness_and_has_no_gate_effect() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_pending_freeze_packet.py"
    spec = importlib.util.spec_from_file_location("validate_t14_pending_freeze_packet", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("study_id", "wrong-study", "custody study drift"),
        ("candidate_manifest_sha256", "0" * 64, "custody candidate drift"),
        ("episode_count", 95, "custody episode count drift"),
        ("key_commitment_sha256", "not-a-hash", "custody hash format drift"),
        ("authority_effect", {}, "custody authority key drift"),
    ],
)
def test_pending_freeze_packet_rejects_malformed_custody_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object, message: str
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_pending_freeze_packet.py"
    spec = importlib.util.spec_from_file_location(
        "validate_t14_pending_freeze_packet_negative", script
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    custody = json.loads(module.CUSTODY_RECEIPT.read_text())
    custody[field] = value
    malformed = tmp_path / "custody.json"
    malformed.write_text(json.dumps(custody))
    monkeypatch.setattr(module, "CUSTODY_RECEIPT", malformed)
    with pytest.raises(ValueError, match=message):
        module.main()
