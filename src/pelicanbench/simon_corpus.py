"""Rights-aware ingestion of Simon Willison's pelican-tag Atom feed.

The default mode exports bibliographic metadata and content fixity only, including
per-entry author attribution. Raw post text is never written unless the caller supplies
a rights status that explicitly permits content redistribution. Derived NLP analysis is
separately gated because public availability does not by itself grant either
redistribution or benchmark-training rights.
"""

from __future__ import annotations

import hashlib
import html
import urllib.request
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from defusedxml import ElementTree

from .empirical_nlp import PromptRecord
from .io import write_json, write_jsonl

ATOM_NAMESPACE = "{http://www.w3.org/2005/Atom}"
DEFAULT_SIMON_ATOM_URL = "https://simonwillison.net/tags/pelican-riding-a-bicycle.atom"
SIMON_CORPUS_SCHEMA_VERSION = "1.0.0"
CONTENT_EXPORT_RIGHTS = frozenset(
    {"licensed", "permission-granted", "public-domain", "author-owned"}
)
DERIVED_ANALYSIS_RIGHTS = CONTENT_EXPORT_RIGHTS | frozenset({"analysis-permitted"})


@dataclass(frozen=True, slots=True)
class SimonCorpusPolicy:
    max_feed_bytes: int = 5_000_000
    max_entries: int = 1_000
    max_entry_text_chars: int = 1_000_000

    def __post_init__(self) -> None:
        for name in ("max_feed_bytes", "max_entries", "max_entry_text_chars"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


class _PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _PlainTextExtractor()
    parser.feed(value)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def _element_text(element: Any | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext())


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SimonAtomEntry:
    source_id: str
    record_id: str
    entry_id: str
    title: str
    author: str | None
    url: str
    published_at: str | None
    updated_at: str | None
    categories: tuple[str, ...]
    content_present: bool
    content_sha256: str | None
    content_text: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SimonAtomCorpus:
    schema_version: str
    source_id: str
    feed_title: str
    feed_url: str
    rights_status: str
    content_exported: bool
    entry_count: int
    entries: tuple[SimonAtomEntry, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "feed_title": self.feed_title,
            "feed_url": self.feed_url,
            "rights_status": self.rights_status,
            "content_exported": self.content_exported,
            "entry_count": self.entry_count,
            "entries_sha256": _sha256_text(
                "\n".join(
                    entry.record_id + "\t" + (entry.content_sha256 or "") for entry in self.entries
                )
            ),
        }


def fetch_atom(
    url: str = DEFAULT_SIMON_ATOM_URL,
    *,
    timeout_seconds: float = 30.0,
    policy: SimonCorpusPolicy | None = None,
) -> bytes:
    """Fetch an Atom feed with an explicit user agent and bounded timeout."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if urlsplit(url).scheme not in ("http", "https"):
        raise ValueError("only http(s) Atom feed URLs are supported")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PelicanBench/0.4 rights-aware corpus metadata importer"},
    )
    selected_policy = policy or SimonCorpusPolicy()
    # Scheme restricted to http/https above; bandit cannot trace the guard.
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
        payload = bytes(response.read(selected_policy.max_feed_bytes + 1))
    if len(payload) > selected_policy.max_feed_bytes:
        raise ValueError("Atom feed exceeds byte limit")
    return payload


def parse_simon_atom(
    payload: bytes | str,
    *,
    source_id: str = "simon-tag-archive",
    rights_status: str = "metadata-only",
    include_content: bool = False,
    policy: SimonCorpusPolicy | None = None,
) -> SimonAtomCorpus:
    """Parse a tag feed without silently exporting copyrighted post text."""

    if include_content and rights_status not in CONTENT_EXPORT_RIGHTS:
        raise PermissionError(
            "raw content export requires licensed, permission-granted, public-domain, or author-owned status"
        )
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    selected_policy = policy or SimonCorpusPolicy()
    if len(raw) > selected_policy.max_feed_bytes:
        raise ValueError("Atom feed exceeds byte limit")
    root = ElementTree.fromstring(raw)
    if root.tag != f"{ATOM_NAMESPACE}feed":
        raise ValueError("expected an Atom feed root")
    feed_title = _element_text(root.find(f"{ATOM_NAMESPACE}title")).strip()
    alternate_link = ""
    for link in root.findall(f"{ATOM_NAMESPACE}link"):
        if link.attrib.get("rel", "alternate") == "alternate" and link.attrib.get("href"):
            alternate_link = str(link.attrib["href"])
            break
    entry_elements = root.findall(f"{ATOM_NAMESPACE}entry")
    if len(entry_elements) > selected_policy.max_entries:
        raise ValueError("Atom entry count exceeds limit")
    entries: list[SimonAtomEntry] = []
    for index, element in enumerate(entry_elements, 1):
        entry_id = _element_text(element.find(f"{ATOM_NAMESPACE}id")).strip()
        title = html.unescape(_plain_text(_element_text(element.find(f"{ATOM_NAMESPACE}title"))))
        author_element = element.find(f"{ATOM_NAMESPACE}author")
        author = (
            _element_text(author_element.find(f"{ATOM_NAMESPACE}name")).strip() or None
            if author_element is not None
            else None
        )
        entry_url = ""
        for link in element.findall(f"{ATOM_NAMESPACE}link"):
            if link.attrib.get("rel", "alternate") == "alternate" and link.attrib.get("href"):
                entry_url = str(link.attrib["href"])
                break
        if not entry_id:
            entry_id = entry_url or f"entry-{index}"
        if not entry_url:
            entry_url = entry_id if entry_id.startswith(("http://", "https://")) else ""
        content_element = element.find(f"{ATOM_NAMESPACE}content")
        if content_element is None:
            content_element = element.find(f"{ATOM_NAMESPACE}summary")
        raw_content = _element_text(content_element)
        plain_content = html.unescape(_plain_text(raw_content)) if raw_content else ""
        if len(plain_content) > selected_policy.max_entry_text_chars:
            raise ValueError(f"Atom entry {index} text exceeds character limit")
        record_digest = hashlib.sha256(f"{source_id}\x1f{entry_id}".encode()).hexdigest()[:20]
        categories = tuple(
            sorted(
                {
                    str(category.attrib["term"])
                    for category in element.findall(f"{ATOM_NAMESPACE}category")
                    if category.attrib.get("term")
                }
            )
        )
        published = _element_text(element.find(f"{ATOM_NAMESPACE}published")).strip() or None
        updated = _element_text(element.find(f"{ATOM_NAMESPACE}updated")).strip() or None
        entries.append(
            SimonAtomEntry(
                source_id=source_id,
                record_id=f"simon:{record_digest}",
                entry_id=entry_id,
                title=title,
                author=author,
                url=entry_url,
                published_at=published,
                updated_at=updated,
                categories=categories,
                content_present=bool(plain_content),
                content_sha256=_sha256_text(plain_content) if plain_content else None,
                content_text=plain_content if include_content and plain_content else None,
            )
        )
    entries.sort(key=lambda item: ((item.published_at or item.updated_at or ""), item.record_id))
    return SimonAtomCorpus(
        schema_version=SIMON_CORPUS_SCHEMA_VERSION,
        source_id=source_id,
        feed_title=feed_title,
        feed_url=alternate_link or DEFAULT_SIMON_ATOM_URL,
        rights_status=rights_status,
        content_exported=include_content,
        entry_count=len(entries),
        entries=tuple(entries),
    )


def corpus_prompt_records(corpus: SimonAtomCorpus) -> tuple[PromptRecord, ...]:
    """Convert authorised post text into the shared empirical-NLP exchange model."""

    if corpus.schema_version != SIMON_CORPUS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported Simon corpus schema {corpus.schema_version!r}; "
            f"expected {SIMON_CORPUS_SCHEMA_VERSION!r}"
        )
    if corpus.rights_status not in DERIVED_ANALYSIS_RIGHTS:
        raise PermissionError("derived content analysis is not permitted for this source status")
    if any(entry.content_present and entry.content_text is None for entry in corpus.entries):
        raise ValueError("content must be retained in-memory to derive NLP records")
    return tuple(
        PromptRecord(
            source_id=entry.source_id,
            record_id=entry.record_id,
            prompt=entry.content_text or "",
            metadata={
                "title": entry.title,
                "url": entry.url,
                "published_at": entry.published_at,
                "updated_at": entry.updated_at,
                "categories": list(entry.categories),
                "content_sha256": entry.content_sha256,
            },
        )
        for entry in corpus.entries
        if entry.content_text
    )


def write_simon_atom_corpus(
    corpus: SimonAtomCorpus,
    output_jsonl: str | Path,
    *,
    summary_path: str | Path | None = None,
) -> tuple[Path, Path]:
    """Write deterministic metadata/content records plus a compact receipt."""

    if corpus.schema_version != SIMON_CORPUS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported Simon corpus schema {corpus.schema_version!r}; "
            f"expected {SIMON_CORPUS_SCHEMA_VERSION!r}"
        )
    if corpus.content_exported and corpus.rights_status not in CONTENT_EXPORT_RIGHTS:
        raise PermissionError(
            "raw content export requires licensed, permission-granted, public-domain, or author-owned status"
        )
    if any(entry.content_text is not None for entry in corpus.entries) and corpus.rights_status not in CONTENT_EXPORT_RIGHTS:
        raise PermissionError(
            "persisting retained content requires licensed, permission-granted, public-domain, or author-owned status"
        )
    output = Path(output_jsonl)
    summary = (
        Path(summary_path) if summary_path is not None else output.with_suffix(".summary.json")
    )
    write_jsonl(output, [entry.as_dict() for entry in corpus.entries])
    write_json(summary, corpus.summary())
    return output, summary


def feed_entry_urls(corpus: SimonAtomCorpus) -> tuple[str, ...]:
    return tuple(entry.url for entry in corpus.entries if entry.url)


def deduplicate_entries(entries: Iterable[SimonAtomEntry]) -> tuple[SimonAtomEntry, ...]:
    """Deduplicate repeated feed pages by canonical entry ID and detect conflicts."""

    by_id: dict[str, SimonAtomEntry] = {}
    for entry in entries:
        existing = by_id.get(entry.entry_id)
        if existing is not None and existing.content_sha256 != entry.content_sha256:
            raise ValueError(f"conflicting content hashes for Atom entry {entry.entry_id}")
        by_id[entry.entry_id] = entry
    return tuple(sorted(by_id.values(), key=lambda item: item.record_id))
