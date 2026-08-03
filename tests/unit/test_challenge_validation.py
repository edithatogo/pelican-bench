from pelicanbench.challenge import commit_challenge, verify_challenge


def test_tampered_reveal_fails():
    public, _ = commit_challenge(
        [{"task_id": "one"}], release="fixture", seed=7, created_at="2026-08-03T00:00:00Z"
    )
    assert not verify_challenge(
        public, [{"task": {"task_id": "other"}, "salt": "bad"}], require_full=True
    )["valid"]
