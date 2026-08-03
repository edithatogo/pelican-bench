import json

from pelicanbench.judge_calibration import evaluate_judge_panel


def test_fixture_panel_passes_but_remains_synthetic(root):
    rows = [
        json.loads(line)
        for line in (root / "benchmark/fixtures/design/judge-calibration-observations.jsonl")
        .read_text()
        .splitlines()
    ]
    policy = json.loads((root / "benchmark/judges/calibration-policy.json").read_text())
    assert evaluate_judge_panel(rows, policy, require_empirical=True)["panel_qualified"]
