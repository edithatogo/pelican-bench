import pytest

from pelicanbench.judge_calibration import evaluate_judge_panel


def test_empty_judge_observations_fail_closed():
    with pytest.raises(ValueError, match="cannot be empty"):
        evaluate_judge_panel([], {"minimum_human_agreement": 0.8})
