from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from pelicanbench.io import file_hash, write_json, write_jsonl
import pelicanbench.study_freeze as freeze

pytestmark = pytest.mark.edge

TASK_HASH = "sha256:" + "a" * 64
PROTOCOL_HASH = "sha256:" + "b" * 64
FILE_HASH = "sha256:" + "c" * 64


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write_json(root / "benchmark/protocol/v1-study-lock.json", {"protocol": "fixed"})
    (root / "docs").mkdir(parents=True)
    (root / "docs/analysis.md").write_text("# Analysis\n", encoding="utf-8")
    write_jsonl(
        root / "results/ledger.jsonl",
        [
            {"event_hash": "sha256:" + "1" * 64},
            {"event_hash": "sha256:" + "2" * 64},
        ],
    )
    return root


def _head(root: Path) -> dict[str, object]:
    path = root / "results/ledger.jsonl"
    return {
        "schema_version": "1.0.0",
        "event_count": 2,
        "last_event_hash": "sha256:" + "2" * 64,
        "ledger_hash": file_hash(path),
        "size_bytes": path.stat().st_size,
    }


def _record_payload(*, freeze_type: str = "analysis-lock") -> dict[str, object]:
    ledger = None if freeze_type == "analysis-lock" else {
        "schema_version": "1.0.0",
        "event_count": 1,
        "last_event_hash": FILE_HASH,
        "ledger_hash": FILE_HASH,
        "size_bytes": 1,
    }
    return {
        "schema_version": "1.0.0",
        "study_id": "PB-STUDY",
        "freeze_type": freeze_type,
        "generated_at": "2026-08-03T00:00:00Z",
        "task_identity_commitment": TASK_HASH,
        "protocol_lock_path": "benchmark/protocol/v1-study-lock.json",
        "protocol_lock_commitment": PROTOCOL_HASH,
        "ledger_head": ledger,
        "files": [{"relative_path": "docs/analysis.md", "sha256": FILE_HASH, "size_bytes": 1}],
        "metadata": {},
        "freeze_commitment": FILE_HASH,
    }


def test_scalar_and_pydantic_contracts_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="unsupported study freeze type"):
        freeze._freeze_type("unknown")
    assert freeze._freeze_type("analysis-lock") == "analysis-lock"
    assert not freeze._valid_sha256("bad")
    assert not freeze._valid_sha256("sha256:" + "A" * 64)
    assert freeze._valid_sha256(TASK_HASH)

    with pytest.raises(ValueError, match="ISO-8601"):
        freeze._validate_timestamp("not-a-time", field="when")
    with pytest.raises(ValueError, match="timezone"):
        freeze._validate_timestamp("2026-08-03T00:00:00", field="when")

    with pytest.raises(TypeError, match="JSON-compatible"):
        freeze._canonical_object({"bad": {1}}, field="metadata")
    monkeypatch.setattr(freeze, "canonical_json", lambda _value: "[]")
    with pytest.raises(TypeError, match="must be an object"):
        freeze._canonical_object({}, field="metadata")

    analysis_with_ledger = _record_payload()
    analysis_with_ledger["ledger_head"] = _record_payload(freeze_type="data-freeze")["ledger_head"]
    with pytest.raises(ValidationError, match="analysis locks cannot contain"):
        freeze.StudyFreezeManifestRecord.model_validate(analysis_with_ledger)

    data_without_ledger = _record_payload(freeze_type="data-freeze")
    data_without_ledger["ledger_head"] = None
    with pytest.raises(ValidationError, match="data freezes require"):
        freeze.StudyFreezeManifestRecord.model_validate(data_without_ledger)

    duplicate = _record_payload()
    duplicate["files"] = [duplicate["files"][0], duplicate["files"][0]]  # type: ignore[index]
    with pytest.raises(ValidationError, match="duplicate file paths"):
        freeze.StudyFreezeManifestRecord.model_validate(duplicate)


def test_ledger_head_and_frozen_file_validation() -> None:
    assert freeze._normalise_ledger_head(None) is None
    with pytest.raises(TypeError, match="must be an object"):
        freeze._normalise_ledger_head({"head": "invalid"})
    with pytest.raises(ValueError, match="verification must be valid"):
        freeze._normalise_ledger_head({"valid": False})

    valid = {
        "schema_version": "1.0.0",
        "event_count": 1,
        "last_event_hash": FILE_HASH,
        "ledger_hash": FILE_HASH,
        "size_bytes": 1,
    }
    malformed = (
        ({"event_count": 1}, "missing"),
        (valid | {"schema_version": "2.0.0"}, "schema"),
        (valid | {"event_count": True}, "event_count"),
        (valid | {"event_count": "1"}, "event_count"),
        (valid | {"size_bytes": False}, "size_bytes"),
        (valid | {"size_bytes": -1}, "size_bytes"),
        (valid | {"ledger_hash": "sha256:BAD"}, "ledger_hash"),
        (valid | {"last_event_hash": 1}, "last_event_hash"),
    )
    for value, message in malformed:
        with pytest.raises(ValueError, match=message):
            freeze._normalise_ledger_head(value)
    assert freeze._normalise_ledger_head({"valid": True, "head": valid}) == valid

    with pytest.raises(ValueError, match="path cannot be blank"):
        freeze.FrozenFile.from_mapping(
            {"relative_path": " ", "sha256": FILE_HASH, "size_bytes": 1}
        )
    with pytest.raises(ValueError, match="size cannot be negative"):
        freeze.FrozenFile.from_mapping(
            {"relative_path": "x", "sha256": FILE_HASH, "size_bytes": -1}
        )
    assert freeze.FrozenFile.from_mapping(
        {"relative_path": "x", "sha256": FILE_HASH, "size_bytes": 0}
    ).relative_path == "x"


def test_ledger_file_matching_covers_corruption_shapes(tmp_path: Path) -> None:
    root = _root(tmp_path)
    path = root / "results/ledger.jsonl"
    head = _head(root)
    assert freeze._ledger_file_matches_head(path, head)
    assert not freeze._ledger_file_matches_head(path, head | {"ledger_hash": FILE_HASH})
    assert not freeze._ledger_file_matches_head(path, head | {"size_bytes": path.stat().st_size + 1})

    malformed = root / "results/malformed.jsonl"
    malformed.write_text("{bad json\n", encoding="utf-8")
    malformed_head = head | {
        "ledger_hash": file_hash(malformed),
        "size_bytes": malformed.stat().st_size,
    }
    assert not freeze._ledger_file_matches_head(malformed, malformed_head)

    empty = root / "results/empty.jsonl"
    empty.write_text("", encoding="utf-8")
    empty_head = head | {
        "ledger_hash": file_hash(empty),
        "size_bytes": 0,
        "event_count": 0,
    }
    assert not freeze._ledger_file_matches_head(empty, empty_head)

    scalar = root / "results/scalar.jsonl"
    scalar.write_text("1\n", encoding="utf-8")
    scalar_head = head | {
        "ledger_hash": file_hash(scalar),
        "size_bytes": scalar.stat().st_size,
        "event_count": 1,
    }
    assert not freeze._ledger_file_matches_head(scalar, scalar_head)

    wrong_final = root / "results/wrong-final.jsonl"
    wrong_final.write_text(json.dumps({"event_hash": FILE_HASH}) + "\n", encoding="utf-8")
    wrong_head = head | {
        "ledger_hash": file_hash(wrong_final),
        "size_bytes": wrong_final.stat().st_size,
        "event_count": 1,
    }
    assert not freeze._ledger_file_matches_head(wrong_final, wrong_head)

    valid_file = freeze.FrozenFile("results/ledger.jsonl", file_hash(path), path.stat().st_size)
    irrelevant = freeze.FrozenFile("docs/analysis.md", FILE_HASH, 1)
    missing = freeze.FrozenFile("results/missing.jsonl", file_hash(path), path.stat().st_size)
    assert freeze._ledger_head_matches_files(root, (irrelevant, missing), head) is False
    assert freeze._ledger_head_matches_files(root, (irrelevant, valid_file), head) is True


def test_manifest_domain_errors_and_verification_branches(tmp_path: Path) -> None:
    root = _root(tmp_path)
    manifest = freeze.build_study_freeze(
        root,
        ("docs/analysis.md",),
        study_id="PB-STUDY",
        freeze_type="analysis-lock",
        task_identity_commitment=TASK_HASH,
        generated_at="2026-08-03T00:00:00Z",
    )

    replacements = (
        (replace(manifest, schema_version="2"), "unsupported study freeze schema"),
        (replace(manifest, study_id=" "), "study_id is required"),
        (replace(manifest, task_identity_commitment="bad"), "task commitment is invalid"),
        (replace(manifest, protocol_lock_commitment="bad"), "protocol commitment is invalid"),
        (replace(manifest, freeze_commitment="bad"), "freeze commitment is invalid"),
        (replace(manifest, ledger_head=_head(root)), "analysis locks cannot contain"),
    )
    for value, message in replacements:
        with pytest.raises(ValueError, match=message):
            freeze.verify_study_freeze(root, value)

    data_shape = replace(manifest, freeze_type="data-freeze")
    with pytest.raises(ValueError, match="data freezes require"):
        freeze.verify_study_freeze(root, data_shape)
    with pytest.raises((TypeError, ValueError), match="JSON"):
        freeze.verify_study_freeze(root, replace(manifest, metadata={"bad": {1}}))

    with pytest.raises(ValueError, match="unsupported study freeze type"):
        freeze.build_study_freeze(
            root,
            ("docs/analysis.md",),
            study_id="PB",
            freeze_type="invalid",  # type: ignore[arg-type]
            task_identity_commitment=TASK_HASH,
        )
    with pytest.raises(ValueError, match="study_id is required"):
        freeze.build_study_freeze(
            root,
            ("docs/analysis.md",),
            study_id=" ",
            freeze_type="analysis-lock",
            task_identity_commitment=TASK_HASH,
        )
    with pytest.raises(ValueError, match="task identity commitment"):
        freeze.build_study_freeze(
            root,
            ("docs/analysis.md",),
            study_id="PB",
            freeze_type="analysis-lock",
            task_identity_commitment="bad",
        )
    with pytest.raises(ValueError, match="timezone"):
        freeze.build_study_freeze(
            root,
            ("docs/analysis.md",),
            study_id="PB",
            freeze_type="analysis-lock",
            task_identity_commitment=TASK_HASH,
            generated_at="2026-08-03T00:00:00",
        )
    with pytest.raises(ValueError, match="at least one input"):
        freeze.build_study_freeze(
            root,
            ("benchmark/protocol/v1-study-lock.json",),
            study_id="PB",
            freeze_type="analysis-lock",
            task_identity_commitment=TASK_HASH,
        )
    with pytest.raises(FileNotFoundError):
        freeze.build_study_freeze(
            root,
            ("docs/missing.md",),
            study_id="PB",
            freeze_type="analysis-lock",
            task_identity_commitment=TASK_HASH,
        )

    mapping_result = freeze.verify_study_freeze(root, manifest.as_dict())
    assert mapping_result.passed
    (root / manifest.protocol_lock_path).unlink()
    missing_protocol = freeze.verify_study_freeze(root, manifest)
    assert not missing_protocol.protocol_lock_matches
    assert not missing_protocol.passed
