from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pelicanbench.simon_corpus import (
    SimonAtomEntry,
    corpus_prompt_records,
    deduplicate_entries,
    feed_entry_urls,
    fetch_atom,
    parse_simon_atom,
    write_simon_atom_corpus,
)

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Pelicans on bicycles</title>
  <link rel="alternate" href="https://example.test/tag/pelican" />
  <entry>
    <id>https://example.test/2026/first</id>
    <title>First &amp; best</title>
    <link rel="alternate" href="https://example.test/2026/first" />
    <published>2026-01-01T00:00:00Z</published>
    <updated>2026-01-02T00:00:00Z</updated>
    <category term="pelican" />
    <category term="svg" />
    <content type="html">&lt;p&gt;Generate an SVG of a pelican riding a bicycle.&lt;/p&gt;</content>
  </entry>
  <entry>
    <title>Second</title>
    <link rel="alternate" href="https://example.test/2026/second" />
    <updated>2026-02-01T00:00:00Z</updated>
    <summary type="html">&lt;p&gt;A heron on a boat.&lt;/p&gt;</summary>
  </entry>
  <entry>
    <title>No content</title>
  </entry>
</feed>
"""


def test_metadata_only_parse_hashes_but_does_not_export_content() -> None:
    corpus = parse_simon_atom(ATOM)
    assert corpus.feed_title == "Pelicans on bicycles"
    assert corpus.feed_url == "https://example.test/tag/pelican"
    assert corpus.entry_count == 3
    assert not corpus.content_exported
    first = next(entry for entry in corpus.entries if entry.title == "First & best")
    assert first.content_present
    assert first.content_sha256 is not None
    assert first.content_text is None
    assert first.categories == ("pelican", "svg")
    assert feed_entry_urls(corpus) == (
        "https://example.test/2026/first",
        "https://example.test/2026/second",
    )
    summary = corpus.summary()
    assert summary["entry_count"] == 3
    assert summary["entries_sha256"].startswith("sha256:")


def test_raw_content_and_derived_records_require_explicit_rights() -> None:
    with pytest.raises(PermissionError, match="raw content export"):
        parse_simon_atom(ATOM, include_content=True)

    corpus = parse_simon_atom(ATOM, rights_status="permission-granted", include_content=True)
    prompts = corpus_prompt_records(corpus)
    assert [item.prompt for item in prompts] == [
        "Generate an SVG of a pelican riding a bicycle.",
        "A heron on a boat.",
    ]
    assert prompts[0].metadata["title"] == "First & best"

    metadata_only = parse_simon_atom(ATOM, rights_status="analysis-permitted")
    with pytest.raises(ValueError, match="retained in-memory"):
        corpus_prompt_records(metadata_only)

    denied = parse_simon_atom(ATOM, rights_status="metadata-only")
    with pytest.raises(PermissionError, match="derived content analysis"):
        corpus_prompt_records(denied)


def test_atom_validation_fallback_identifiers_and_deterministic_writes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Atom feed root"):
        parse_simon_atom("<rss/>")

    corpus = parse_simon_atom(ATOM, rights_status="licensed", include_content=True)
    output, summary = write_simon_atom_corpus(corpus, tmp_path / "entries.jsonl")
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    receipt = json.loads(summary.read_text(encoding="utf-8"))
    assert len(rows) == 3
    assert any(row["entry_id"] == "entry-3" for row in rows)
    assert receipt == corpus.summary()


def test_deduplication_accepts_identical_entries_and_rejects_conflicts() -> None:
    entry = SimonAtomEntry(
        source_id="fixture",
        record_id="record:1",
        entry_id="entry:1",
        title="A",
        url="https://example.test/a",
        published_at=None,
        updated_at=None,
        categories=(),
        content_present=True,
        content_sha256="sha256:" + "a" * 64,
    )
    assert deduplicate_entries([entry, entry]) == (entry,)
    conflict = SimonAtomEntry(**{**entry.as_dict(), "content_sha256": "sha256:" + "b" * 64})
    with pytest.raises(ValueError, match="conflicting content hashes"):
        deduplicate_entries([entry, conflict])


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_fetch_atom_has_positive_timeout_and_bounded_network_call() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        fetch_atom(timeout_seconds=0)
    with patch(
        "pelicanbench.simon_corpus.urllib.request.urlopen", return_value=_Response(b"feed")
    ) as call:
        assert fetch_atom("https://example.test/feed.atom", timeout_seconds=4.5) == b"feed"
    request = call.call_args.args[0]
    assert request.full_url == "https://example.test/feed.atom"
    assert call.call_args.kwargs["timeout"] == 4.5
