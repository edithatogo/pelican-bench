from __future__ import annotations

import hashlib
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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "0.0.0", "custody verification schema drift"),
        ("alias_manifest_sha256", "0" * 64, "custody verification alias drift"),
        ("assignment_count", 105, "custody verification assignment drift"),
        ("authority_effect", {}, "custody verification authority key drift"),
    ],
)
def test_pending_freeze_packet_rejects_semantically_rebound_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object, message: str
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_pending_freeze_packet.py"
    spec = importlib.util.spec_from_file_location(
        "validate_t14_pending_freeze_verification", script
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verification = json.loads(module.CUSTODY_VERIFICATION.read_text())
    verification[field] = value
    rebound_verification = tmp_path / "verification.json"
    rebound_verification.write_text(json.dumps(verification))
    packet = json.loads(module.PACKET.read_text())
    packet["procedural_custody_verification_sha256"] = hashlib.sha256(
        rebound_verification.read_bytes()
    ).hexdigest()
    rebound_packet = tmp_path / "packet.json"
    rebound_packet.write_text(json.dumps(packet))
    monkeypatch.setattr(module, "CUSTODY_VERIFICATION", rebound_verification)
    monkeypatch.setattr(module, "PACKET", rebound_packet)
    with pytest.raises(ValueError, match=message):
        module.main()
