from pelicanbench.qualification import load_default_model_qualification_plan
from pelicanbench.qualification_runner import run_fixture_model_qualification


def test_fixture_qualification_is_resumable(root, tmp_path):
    plan = load_default_model_qualification_plan(root)
    first = run_fixture_model_qualification(plan, model_id="openai/gpt-5.6-terra", output=tmp_path)
    second = run_fixture_model_qualification(plan, model_id="openai/gpt-5.6-terra", output=tmp_path)
    assert (first["executed_cells"], second["resumed_cells"]) == (9, 9)
    assert first["outcome_hash"] == second["outcome_hash"]
