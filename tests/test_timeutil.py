from __future__ import annotations

from datetime import UTC, datetime

from pelicanbench.timeutil import utc_now, utc_now_iso


def test_time_helpers_support_fixed_and_live_time(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert utc_now() == datetime(1970, 1, 1, tzinfo=UTC)
    assert utc_now_iso() == "1970-01-01T00:00:00Z"

    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    before = datetime.now(tz=UTC)
    observed = utc_now()
    after = datetime.now(tz=UTC)
    assert before <= observed <= after
