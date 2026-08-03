from pelicanbench.calibration_ops import build_adjudication_queue


def test_fixture_calibration_builds_adjudication_queue(root):
    import json

    rows = [
        json.loads(line)
        for line in (root / "benchmark/fixtures/human-calibration/operations-responses.jsonl")
        .read_text()
        .splitlines()
    ]
    assert len(build_adjudication_queue(rows)) == 4
