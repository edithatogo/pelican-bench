from __future__ import annotations

import pytest

from pelicanbench.simon_corpus import SimonCorpusPolicy, parse_simon_atom


def _feed(entries: str) -> str:
    return f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'


@pytest.mark.edge
def test_simon_corpus_rejects_oversized_feed_before_xml_parsing() -> None:
    with pytest.raises(ValueError, match="feed exceeds byte limit"):
        parse_simon_atom(b"x" * 17, policy=SimonCorpusPolicy(max_feed_bytes=16))


@pytest.mark.edge
def test_simon_corpus_rejects_entry_count_exhaustion() -> None:
    entries = "".join(f"<entry><id>{index}</id></entry>" for index in range(3))
    with pytest.raises(ValueError, match="entry count exceeds limit"):
        parse_simon_atom(_feed(entries), policy=SimonCorpusPolicy(max_entries=2))


@pytest.mark.edge
def test_simon_corpus_rejects_oversized_entry_text() -> None:
    payload = _feed("<entry><id>x</id><content>12345</content></entry>")
    with pytest.raises(ValueError, match="text exceeds character limit"):
        parse_simon_atom(payload, policy=SimonCorpusPolicy(max_entry_text_chars=4))


@pytest.mark.edge
@pytest.mark.parametrize("field", ["max_feed_bytes", "max_entries", "max_entry_text_chars"])
def test_simon_corpus_policy_rejects_non_positive_budgets(field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} must be positive"):
        SimonCorpusPolicy(**{field: 0})
