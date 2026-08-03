from pelicanbench.design_assurance import build_design_assurance_report
from pelicanbench.io import read_json, read_jsonl


def test_default_design_assurance_is_machine_readable(root):
    report = build_design_assurance_report(
        read_jsonl(root / "benchmark/tasks/v1-candidate.jsonl"),
        read_json(root / "benchmark/models/prospective-panel.json"),
        read_json(root / "benchmark/human-calibration/study-spec.json"),
        read_json(root / "benchmark/design/assumptions.json"),
    )
    assert report.as_dict()["schema_version"] == "1.0.0"
