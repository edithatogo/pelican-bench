from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def test_freeze_packet_binds_exact_hashes_and_limits_gate_effect() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_pending_freeze_packet.py"
    spec = importlib.util.spec_from_file_location("validate_t14_pending_freeze_packet", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
    packet = json.loads(module.PACKET.read_text())
    assert packet["freeze_effect"] is True
    assert packet["normative_manifest"]["frozen"] is True
    assert all(
        packet[key] is False
        for key in (
            "ratings_authorized",
            "score_promotion",
            "release_authorized",
            "publication_authorized",
            "unblinding_authorized",
        )
    )


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


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("classification", "independent", True), "freeze independence overclaim"),
        (("authority_effect", "ratings", True), "freeze receipt overclaims downstream"),
        (("frozen_commitments", "candidate_manifest_sha256", "0" * 64), "freeze candidate drift"),
    ],
)
def test_freeze_packet_rejects_semantically_rebound_decision_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: tuple[str, str, object],
    message: str,
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/validate_t14_pending_freeze_packet.py"
    spec = importlib.util.spec_from_file_location("validate_t14_freeze_receipt", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    freeze = json.loads(module.FREEZE_RECEIPT.read_text())
    section, field, value = mutation
    freeze[section][field] = value
    rebound_freeze = tmp_path / "freeze.json"
    rebound_freeze.write_text(json.dumps(freeze))
    packet = json.loads(module.PACKET.read_text())
    packet["pending_required_inputs"]["steward_freeze_decision_receipt_sha256"] = hashlib.sha256(
        rebound_freeze.read_bytes()
    ).hexdigest()
    rebound_packet = tmp_path / "packet.json"
    rebound_packet.write_text(json.dumps(packet))
    monkeypatch.setattr(module, "FREEZE_RECEIPT", rebound_freeze)
    monkeypatch.setattr(module, "PACKET", rebound_packet)
    with pytest.raises(ValueError, match=message):
        module.main()
