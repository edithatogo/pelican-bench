from pelicanbench.blinding import build_blinding_manifests, verify_blinding_manifests


def test_blinding_manifest_roundtrip():
    key = "fixture-secret-contains-at-least-32-bytes"
    public, private = build_blinding_manifests(
        ["model/a", "model/b"],
        study_id="fixture",
        key=key,
        task_identity_commitment="sha256:" + "1" * 64,
    )
    assert verify_blinding_manifests(public, private, key=key).passed
