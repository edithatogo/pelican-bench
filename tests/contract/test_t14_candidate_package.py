from __future__ import annotations

import importlib.util
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
