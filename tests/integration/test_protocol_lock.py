from pelicanbench.protocol import verify_study_protocol


def test_committed_protocol_lock_verifies(root):
    assert verify_study_protocol(root, root / "benchmark/protocol/v1-study-lock.json").valid
