"""Synthetic storage experiments: no real assignments, tokens, answers or collection."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest
from t14_storage_fixture import Denied, SyntheticStore

pytestmark = pytest.mark.contract


@pytest.fixture
def store(tmp_path: Path) -> SyntheticStore:
    return SyntheticStore(tmp_path)


def test_retry_and_conflict(store: SyntheticStore) -> None:
    receipt = store.save("synthetic-session-a", "synthetic-a1", "key-1", "synthetic-yes")
    assert store.save("synthetic-session-a", "synthetic-a1", "key-1", "synthetic-yes") == receipt
    for key, answer in [("key-1", "synthetic-abstain"), ("key-2", "synthetic-yes")]:
        with pytest.raises(Denied, match="conflict"):
            store.save("synthetic-session-a", "synthetic-a1", key, answer)
    assert store.resume("synthetic-session-a") == [("synthetic-a1", receipt)]
    assert "synthetic" not in receipt


@pytest.mark.parametrize(
    "field,value",
    [
        ("active", 0),
        ("authority", "D045"),
        ("study", "other"),
        ("protocol", "other"),
        ("consent", "other"),
        ("assets", "other"),
        ("expires", 10),
    ],
)
def test_live_authority_rechecked(store: SyntheticStore, field: str, value: object) -> None:
    store.save("synthetic-session-a", "synthetic-a1", "key-1", "synthetic-yes")
    # Column comes only from this fixed test parameter list, not request data.
    with store.connect() as db:
        db.execute(f"UPDATE policy SET {field} = ?", (value,))
    with pytest.raises(Denied, match="denied"):
        store.save("synthetic-session-a", "synthetic-a1", "key-1", "synthetic-yes")
    with pytest.raises(Denied, match="denied"):
        store.resume("synthetic-session-a")


@pytest.mark.parametrize("session", ["", "D045", "synthetic-unknown"])
def test_unknown_sessions(store: SyntheticStore, session: str) -> None:
    with pytest.raises(Denied, match="denied"):
        store.resume(session)


def test_participant_isolation_and_scoped_keys(store: SyntheticStore) -> None:
    first = store.save("synthetic-session-a", "synthetic-a1", "same-key", "synthetic-yes")
    for alias in ["synthetic-a1", "does-not-exist"]:
        with pytest.raises(Denied, match=r"^denied$"):
            store.save("synthetic-session-b", alias, "same-key", "synthetic-yes")
    assert store.resume("synthetic-session-b") == []
    second = store.save("synthetic-session-b", "synthetic-b1", "same-key", "synthetic-yes")
    assert first != second
    assert store.resume("synthetic-session-b") == [("synthetic-b1", second)]


def test_session_expiry_consent_and_missing_policy(store: SyntheticStore) -> None:
    with store.connect() as db:
        db.execute("UPDATE sessions SET consent = 'wrong'")
    with pytest.raises(Denied):
        store.resume("synthetic-session-a")
    with store.connect() as db:
        db.execute("UPDATE sessions SET consent = 'synthetic-consent-v0', expires = 10")
    with pytest.raises(Denied):
        store.resume("synthetic-session-a")
    with store.connect() as db:
        db.execute("DELETE FROM policy")
    with pytest.raises(Denied):
        store.resume("synthetic-session-a")


def test_cap_retries_and_schema(store: SyntheticStore) -> None:
    receipt = store.save("synthetic-session-a", "synthetic-a1", "key-1", "synthetic-abstain")
    assert (
        store.save("synthetic-session-a", "synthetic-a1", "key-1", "synthetic-abstain") == receipt
    )
    with pytest.raises(Denied, match="cap"):
        store.save("synthetic-session-a", "synthetic-a2", "key-2", "synthetic-yes")
    for answer in ["human answer", "", "x" * 10000]:
        with pytest.raises(Denied, match="schema"):
            store.save("synthetic-session-b", "synthetic-b1", "key", answer)
    with pytest.raises(Denied, match="schema"):
        store.save("synthetic-session-b", "synthetic-b1", "x" * 65, "synthetic-yes")
    with pytest.raises(TypeError):
        store.save("synthetic-session-b", "synthetic-b1", "key", "synthetic-yes", extra="no")  # type: ignore[call-arg]


@pytest.mark.parametrize("different", [False, True])
def test_concurrent_saves(store: SyntheticStore, different: bool) -> None:
    def save(index: int) -> str:
        try:
            answer = "synthetic-abstain" if different and index else "synthetic-yes"
            return store.save("synthetic-session-a", "synthetic-a1", "key", answer)
        except Denied as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, [0, 1]))
    assert len(store.resume("synthetic-session-a")) == 1
    if different:
        assert results.count("conflict") == 1
    else:
        assert results[0] == results[1]


def test_commit_before_ack_and_rollback(store: SyntheticStore) -> None:
    with pytest.raises(Denied, match="simulated-lost-ack"):
        store.save(
            "synthetic-session-a", "synthetic-a1", "key", "synthetic-yes", fault="after-commit"
        )
    receipt = store.resume("synthetic-session-a")[0][1]
    assert store.save("synthetic-session-a", "synthetic-a1", "key", "synthetic-yes") == receipt
    with pytest.raises(Denied, match="storage-unavailable"):
        store.save("synthetic-session-b", "synthetic-b1", "key", "synthetic-yes", fault="disk-full")
    assert store.resume("synthetic-session-b") == []
    store.save("synthetic-session-b", "synthetic-b1", "key", "synthetic-yes")


def test_locked_and_missing_storage(store: SyntheticStore) -> None:
    with store.connect() as db:
        db.execute("BEGIN EXCLUSIVE")
        with pytest.raises(Denied, match="storage-unavailable"):
            store.save("synthetic-session-a", "synthetic-a1", "key", "synthetic-yes")
    store.path.rename(store.path.with_suffix(".unavailable"))
    with pytest.raises(Denied, match="storage-unavailable"):
        store.resume("synthetic-session-a")
    assert not store.path.exists()


def test_snapshot_restore_and_stale_restore_denial(store: SyntheticStore) -> None:
    receipt = store.save("synthetic-session-a", "synthetic-a1", "key", "synthetic-yes")
    with closing(sqlite3.connect(":memory:")) as snapshot, store.connect() as db:
        db.backup(snapshot)
        # Simulate a lost response table and restore the whole response database.
        db.execute("DELETE FROM responses")
        db.commit()
        snapshot.backup(db)
        assert store.save("synthetic-session-a", "synthetic-a1", "key", "synthetic-yes") == receipt
        store.withdraw("synthetic-withdraw-a")
        snapshot.backup(db)
        # Withdrawal control is separate and must survive response-store restoration.
        with pytest.raises(Denied):
            store.resume("synthetic-session-a")


def test_withdrawal_is_not_erasure(store: SyntheticStore) -> None:
    store.save("synthetic-session-a", "synthetic-a1", "key", "synthetic-yes")
    for token in ["synthetic-session-a", "unknown"]:
        with pytest.raises(Denied, match=r"^denied$"):
            store.withdraw(token)
    store.withdraw("synthetic-withdraw-a")
    store.withdraw("synthetic-withdraw-a")
    with pytest.raises(Denied):
        store.save("synthetic-session-a", "synthetic-a1", "key", "synthetic-yes")
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM responses").fetchone()[0] == 1


def test_failure_messages_do_not_echo_payload(
    store: SyntheticStore, caplog: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(Denied) as caught:
        store.save("synthetic-session-a", "synthetic-a1", "private-key", "private-answer")
    assert str(caught.value) == "schema"
    assert caplog.text == ""


def test_missing_control_does_not_recreate_authorization(store: SyntheticStore) -> None:
    store.control.rename(store.control.with_suffix(".unavailable"))
    with pytest.raises(Denied, match="storage-unavailable"):
        store.resume("synthetic-session-a")
    with pytest.raises(Denied, match="storage-unavailable"):
        store.withdraw("synthetic-withdraw-a")
    assert not store.control.exists()
