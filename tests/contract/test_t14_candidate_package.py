from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/validate_t14_candidate_episodes.py"
SPEC = importlib.util.spec_from_file_location("validate_t14_candidate_episodes", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_candidate_asset_resolution_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="resolves outside candidate root"):
        MODULE.resolve_candidate_asset(Path("benchmark/fixtures/repair/candidate/../../tasks.json"))


def test_candidate_asset_resolution_accepts_committed_asset() -> None:
    resolved = MODULE.resolve_candidate_asset(
        Path("benchmark/fixtures/repair/candidate/assets/repair-t14-candidate-01-01-before.svg")
    )
    assert resolved.is_file()


def test_wheel_geometry_extracts_target_specific_coordinates() -> None:
    geometry = MODULE.wheel_geometry(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<circle data-role="front-wheel" cx="10" cy="20" r="5"/>'
        '<circle data-role="rear-wheel" cx="30" cy="40" r="5"/>'
        "</svg>"
    )
    assert geometry == {"front-wheel": (10.0, 20.0, 5.0), "rear-wheel": (30.0, 40.0, 5.0)}


@pytest.mark.parametrize(
    "svg, message",
    [
        (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<circle data-role="front-wheel" cx="10" cy="20" r="5"/>'
            "</svg>",
            "wheel geometry incomplete",
        ),
        (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<circle data-role="front-wheel" cx="10" cy="20" r="0"/>'
            '<circle data-role="rear-wheel" cx="30" cy="40" r="5"/>'
            "</svg>",
            "non-positive front-wheel radius",
        ),
    ],
)
def test_wheel_geometry_fails_closed(svg: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        MODULE.wheel_geometry(svg)


def test_pedal_contact_geometry_extracts_endpoint() -> None:
    pedal, endpoint = MODULE.pedal_contact_geometry(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<circle data-role="pedal" cx="20" cy="30" r="4"/>'
        '<path data-role="foot pedal contact" d="M1 2 L10 11 L18 29"/>'
        "</svg>"
    )
    assert pedal == (20.0, 30.0)
    assert endpoint == (18.0, 29.0)


def test_candidate_design_is_clustered_crossed_and_unfrozen() -> None:
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "benchmark/fixtures/repair/candidate/manifest.json"
        ).read_text()
    )
    assert manifest["episode_count"] == 96
    assert manifest["scene_group_count"] == 24
    assert manifest["episodes_per_scene_group"] == 4
    assert manifest["split_policy"]["development_count"] == 72
    assert manifest["split_policy"]["held_out_count"] == 24
    assert manifest["normative_sample_frozen"] is False
    for family in {row["defect_family"] for row in manifest["episodes"]}:
        rows = [row for row in manifest["episodes"] if row["defect_family"] == family]
        assert [row["severity"] for row in rows].count("moderate") == 6
        assert [row["severity"] for row in rows].count("severe") == 6


def test_scene_geometry_signature_uses_visible_geometry() -> None:
    first = '<svg xmlns="http://www.w3.org/2000/svg"><path data-role="ground" d="M0 9L9 9"/><circle data-role="front-wheel" cx="8" cy="8" r="2"/><circle data-role="rear-wheel" cx="2" cy="8" r="2"/><path data-role="frame" d="M2 8L8 8"/></svg>'
    second = first.replace('cx="8" cy="8"', 'cx="9" cy="8"', 1)
    assert MODULE.scene_geometry_signature(first) != MODULE.scene_geometry_signature(second)
