"""Test-only SQLite model with a closed synthetic vocabulary; not a collection service.

No HTTP, CLI, enrollment, actual rubric, production authorization or asset access exists.
Control state is deliberately outside response snapshots. Its loss must fail closed.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4


class Denied(ValueError):
    """Allowlisted failure code, never request data or a raw database exception."""


class SyntheticStore:
    """Two pre-created toy participants only, one saved response each, logical time 10."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "synthetic-responses.sqlite"
        self.control = directory / "synthetic-control.sqlite"
        for path in (self.path, self.control):
            path.touch(mode=0o600, exist_ok=False)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE control.policy (
                    active INTEGER, authority TEXT, study TEXT, protocol TEXT,
                    consent TEXT, assets TEXT, expires INTEGER, cap INTEGER
                );
                INSERT INTO control.policy VALUES (
                    1, 'synthetic-only-v0', 'synthetic-study-v0', 'synthetic-protocol-v0',
                    'synthetic-consent-v0', 'synthetic-assets-v0', 100, 1
                );
                CREATE TABLE control.sessions (
                    token TEXT PRIMARY KEY, participant TEXT UNIQUE, consent TEXT,
                    expires INTEGER, withdrawn INTEGER, withdrawal TEXT UNIQUE
                );
                INSERT INTO control.sessions VALUES
                    ('synthetic-session-a', 'synthetic-a', 'synthetic-consent-v0',
                     100, 0, 'synthetic-withdraw-a'),
                    ('synthetic-session-b', 'synthetic-b', 'synthetic-consent-v0',
                     100, 0, 'synthetic-withdraw-b');
                CREATE TABLE control.assignments (participant TEXT, alias TEXT PRIMARY KEY);
                INSERT INTO control.assignments VALUES
                    ('synthetic-a', 'synthetic-a1'), ('synthetic-a', 'synthetic-a2'),
                    ('synthetic-b', 'synthetic-b1');
                CREATE TABLE responses (
                    participant TEXT, alias TEXT, request_key TEXT, answer TEXT, receipt TEXT,
                    PRIMARY KEY (participant, alias), UNIQUE (participant, alias, request_key)
                );
            """)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Never recreate a missing database. Always close even on rollback or failure."""
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=0.2)) as db:
            db.execute("ATTACH DATABASE ? AS control", (self.control.as_uri() + "?mode=rw",))
            db.execute("PRAGMA synchronous = FULL")
            db.execute("PRAGMA control.synchronous = FULL")
            with db:
                yield db

    @staticmethod
    def authorize(db: sqlite3.Connection, session: str) -> tuple[str, int]:
        policy = db.execute("SELECT * FROM control.policy").fetchall()
        expected = (
            1,
            "synthetic-only-v0",
            "synthetic-study-v0",
            "synthetic-protocol-v0",
            "synthetic-consent-v0",
            "synthetic-assets-v0",
        )
        if len(policy) != 1 or policy[0][:6] != expected or policy[0][6] <= 10:
            raise Denied("denied")
        row = db.execute(
            "SELECT participant, consent, expires, withdrawn FROM control.sessions WHERE token = ?",
            (session,),
        ).fetchone()
        if row is None or row[1] != expected[4] or row[2] <= 10 or row[3] != 0:
            raise Denied("denied")
        return str(row[0]), int(policy[0][7])

    def save(self, session: str, alias: str, key: str, answer: str, *, fault: str = "") -> str:
        """Commit before ack; named fault hooks are test-only and cannot call providers."""
        if answer not in {"synthetic-yes", "synthetic-abstain"} or not 1 <= len(key) <= 64:
            raise Denied("schema")
        if fault not in {"", "disk-full", "after-commit"}:
            raise Denied("schema")
        try:
            with self.connect() as db:
                # Serialize authorization, cap check and response write against revocation.
                db.execute("BEGIN IMMEDIATE")
                participant, cap = self.authorize(db, session)
                entitled = db.execute(
                    "SELECT 1 FROM control.assignments WHERE participant = ? AND alias = ?",
                    (participant, alias),
                ).fetchone()
                if entitled is None:
                    raise Denied("denied")
                row = db.execute(
                    "SELECT request_key, answer, receipt FROM responses WHERE participant = ? AND alias = ?",
                    (participant, alias),
                ).fetchone()
                if row is not None:
                    if row[:2] != (key, answer):
                        raise Denied("conflict")
                    return str(row[2])
                count = db.execute(
                    "SELECT count(*) FROM responses WHERE participant = ?",
                    (participant,),
                ).fetchone()[0]
                if count >= cap:
                    raise Denied("cap")
                receipt = uuid4().hex
                db.execute(
                    "INSERT INTO responses VALUES (?, ?, ?, ?, ?)",
                    (participant, alias, key, answer, receipt),
                )
                if fault == "disk-full":
                    # Fault injection models the database error; not physical disk exhaustion.
                    raise sqlite3.OperationalError("synthetic disk full")
            if fault == "after-commit":
                raise Denied("simulated-lost-ack")
            return receipt
        except sqlite3.Error:
            raise Denied("storage-unavailable") from None

    def resume(self, session: str) -> list[tuple[str, str]]:
        """Only own opaque completion receipts; no answer or hidden map is returned."""
        try:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                participant, _ = self.authorize(db, session)
                return [
                    (str(row[0]), str(row[1]))
                    for row in db.execute(
                        "SELECT alias, receipt FROM responses WHERE participant = ? ORDER BY alias",
                        (participant,),
                    )
                ]
        except sqlite3.Error:
            raise Denied("storage-unavailable") from None

    def withdraw(self, token: str) -> None:
        """Logical withdrawal only: not erasure, consent, analysis or release authority."""
        try:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                result = db.execute(
                    "UPDATE control.sessions SET withdrawn = 1 WHERE withdrawal = ?",
                    (token,),
                )
                if result.rowcount != 1:
                    raise Denied("denied")
        except sqlite3.Error:
            raise Denied("storage-unavailable") from None
