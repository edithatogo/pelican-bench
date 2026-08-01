from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.drift import compare_distributions
from pelicanbench.ecosystem import INTEGRATIONS, locate_sibling_repositories
from pelicanbench.image_analysis import analyse_raster, analyse_svg
from pelicanbench.media_contracts import FrameObservation, score_sequence
from pelicanbench.registry import ModelRegistryEntry, eligible_models, load_registry, registry_summary


def test_drift_actions():
    no_drift = compare_distributions([0.5]*20,[0.5]*20)
    assert no_drift.action == "none"
    drift = compare_distributions([0.1]*20,[0.9]*20)
    assert drift.action == "new-major-release-and-bridge-study"
    with pytest.raises(ValueError):
        compare_distributions([], [0.2])
    with pytest.raises(ValueError):
        compare_distributions([2], [0.2])


def test_registry(root: Path):
    entries = load_registry(root / "hf/model-eligibility.json")
    assert registry_summary(entries)["models"] >= 1
    assert all(not item.remote_code_required for item in eligible_models(entries, track="compositional-svg"))
    blocked = ModelRegistryEntry(model_id="x",revision="r",tracks=("t",),access_type="x",license_status="eligible",remote_code_required=True)
    assert not blocked.eligible


def test_ecosystem_discovery(tmp_path: Path):
    (tmp_path / "krita-cli").mkdir()
    project = tmp_path / "pelican-bench"
    project.mkdir()
    found = locate_sibling_repositories(project)
    assert found["edithatogo/krita-cli"].endswith("krita-cli")
    assert len(INTEGRATIONS) >= 6


def test_media_sequence():
    sequence = score_sequence([FrameObservation(0,1,0.8,0.9),FrameObservation(1,0.9,0.7,0.8)])
    assert sequence.frames == 2
    assert sequence.worst_frame < 1
    with pytest.raises(ValueError):
        FrameObservation(0,2,0,0)
    with pytest.raises(ValueError):
        score_sequence([])


def test_image_analysis(valid_svg: str):
    features = analyse_svg(valid_svg)
    assert features["valid"]
    assert features["anatomy_role_count"] >= 4


def test_raster_analysis():
    PIL = pytest.importorskip("PIL")
    from PIL import Image
    import io
    image=Image.new("RGB",(10,5),(128,64,32))
    buf=io.BytesIO(); image.save(buf,format="PNG")
    result=analyse_raster(buf.getvalue())
    assert result["aspect_ratio"]==2
    assert len(result["channel_means"])==3
