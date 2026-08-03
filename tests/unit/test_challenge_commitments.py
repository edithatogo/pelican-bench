from pelicanbench.challenge import commit_challenge


def test_commitments_are_deterministic():
    args = {"release": "fixture", "seed": 7, "created_at": "2026-08-03T00:00:00Z"}
    assert commit_challenge([{"task_id": "one"}], **args) == commit_challenge(
        [{"task_id": "one"}], **args
    )
