import json

from pelicanbench.power_simulation import simulate_design_power


def test_power_fixture_matches_snapshot(root):
    actual = simulate_design_power(
        json.loads((root / "benchmark/design/power-simulation.json").read_text())
    )
    expected = json.loads((root / "benchmark/evidence/snapshots/power-simulation.json").read_text())
    assert actual == expected
