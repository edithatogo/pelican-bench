"""Participant-facing inactive package has no collection or study surfaces."""

from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

pytestmark = pytest.mark.contract
PACKAGE = Path(__file__).resolve().parents[2] / "hf/t14-workflow-preview-v2"


class Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def parsed() -> tuple[str, Elements]:
    document = (PACKAGE / "index.html").read_text()
    elements = Elements()
    elements.feed(document)
    return document, elements


def test_exact_allowlist_and_no_study_dependencies() -> None:
    assert {path.name for path in PACKAGE.iterdir()} == {"README.md", "index.html", "style.css"}
    assert all(path.is_file() and not path.is_symlink() for path in PACKAGE.iterdir())
    content = "\n".join(path.read_text() for path in PACKAGE.iterdir())
    for forbidden in (
        "benchmark/preparation",
        "D044",
        "episode_id",
        "scene_id",
        "source_group",
        "target_constructed_complete",
        "protected_constructed_changed",
        "heldout",
        "localStorage",
        "sessionStorage",
        "fetch(",
        "XMLHttpRequest",
    ):
        assert forbidden not in content
    readme = (PACKAGE / "README.md").read_text()
    assert "sdk: static" in readme and "app_file: index.html" in readme
    assert "not deployment authority" in readme


def test_no_executable_or_external_surfaces() -> None:
    _, elements = parsed()
    assert not {
        "script",
        "form",
        "iframe",
        "object",
        "embed",
        "button",
        "base",
        "textarea",
    }.intersection(tag for tag, _ in elements.tags)
    ids = [attrs["id"] for _, attrs in elements.tags if "id" in attrs]
    assert len(ids) == len(set(ids))
    for tag, attrs in elements.tags:
        if tag == "meta":
            assert str(attrs.get("http-equiv", "")).strip().lower() != "refresh"
        assert not any(key.lower().startswith("on") for key in attrs)
        assert not {"action", "formaction", "src", "srcset", "style", "ping"}.intersection(attrs)
        if "href" in attrs:
            href = str(attrs["href"])
            assert href == "style.css" or (href.startswith("#") and href[1:] in ids)
        for reference in str(attrs.get("aria-labelledby", "")).split():
            assert reference in ids
    policy = next(
        str(attrs["content"])
        for tag, attrs in elements.tags
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"
    )
    for directive in (
        "default-src 'none'",
        "connect-src 'none'",
        "form-action 'none'",
        "base-uri 'none'",
    ):
        assert directive in policy
    stylesheet = (PACKAGE / "style.css").read_text().lower()
    assert "url(" not in stylesheet and "@import" not in stylesheet
    assert "outline" in stylesheet and "@media" in stylesheet


def test_disabled_unselected_separate_questions() -> None:
    _, elements = parsed()
    inputs = [attrs for tag, attrs in elements.tags if tag == "input"]
    labels = {attrs.get("for") for tag, attrs in elements.tags if tag == "label"}
    assert len(inputs) == 8
    assert all(
        attrs.get("type") == "radio"
        and "disabled" in attrs
        and "checked" not in attrs
        and attrs["id"] in labels
        for attrs in inputs
    )
    assert {attrs["name"] for attrs in inputs} == {"toy-target", "toy-other"}
    for group in ("toy-target", "toy-other"):
        assert {attrs["value"] for attrs in inputs if attrs["name"] == group} == {
            "yes",
            "no",
            "cannot-judge",
            "prefer-not",
        }
    assert (
        len([1 for tag, attrs in elements.tags if tag == "fieldset" and "disabled" in attrs]) == 2
    )


def test_original_inline_toy_pair() -> None:
    document, elements = parsed()
    assert len([1 for tag, _ in elements.tags if tag == "svg"]) == 2
    diagrams = []
    for fragment in document.split("<svg")[1:]:
        markup = "<svg" + fragment.split("</svg>", 1)[0] + "</svg>"
        diagram = ET.fromstring(markup)
        assert diagram.attrib["viewBox"] == "0 0 360 200"
        assert diagram.find("title") is not None and diagram.find("desc") is not None
        assert {child.tag for child in diagram} <= {"title", "desc", "path", "rect"}
        diagrams.append(markup)
    assert len(set(diagrams)) == 2


def test_approval_and_future_use_boundaries() -> None:
    document, _ = parsed()
    for notice in (
        "No responses are collected",
        "approver, not a required rater",
        "not a recruitment invitation",
        "This preview cannot record consent",
        "no study assignments",
        "not an approved",
        "not a qualification test",
        "Public workflow code does not mean public raw responses",
        "Contributions remain quarantined",
        "separate approval",
        "historical frozen evidence is preserved",
        "synthetic and non-independent",
        "Agent advice is never relabeled as human classification",
    ):
        assert notice in document
