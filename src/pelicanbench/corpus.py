"""Fixture-scale, explainable NLP/NER pipeline and idea coverage."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .io import content_hash
from .timeutil import utc_now_iso

ENTITY_PATTERNS: dict[str, tuple[str, ...]] = {
    "ANIMAL": ("pelican", "flamingo", "heron", "stork", "bird"),
    "MOBILE_OBJECT": ("bicycle", "bike", "tuk-tuk", "scooter", "wheelchair"),
    "ANATOMY": ("bill", "pouch", "wing", "feet", "foot", "body", "silhouette"),
    "MECHANICS": ("wheel", "frame", "pedal", "handlebar", "saddle", "cabin"),
    "EVALUATION": ("recognisable", "criticised", "praised", "improved", "failed", "extra"),
    "AGENTIC": ("agent", "inspected", "contact sheet", "reference", "revision", "preserved"),
}
RELATION_PATTERNS = {
    "failed_contact": re.compile(r"(?:did not|not) contact", re.I),
    "disconnected_component": re.compile(r"disconnected", re.I),
    "improvement": re.compile(r"improv(?:e|ed|ement)", re.I),
    "regression": re.compile(r"introduced|extra|regress", re.I),
    "role_mismatch": re.compile(r"rather than|represented .* rather than", re.I),
}
CATEGORY_PATTERNS = {
    "anatomy": re.compile(r"bill|pouch|wing|feet|foot|anatom", re.I),
    "mechanics": re.compile(r"wheel|frame|pedal|handlebar|saddle|cabin", re.I),
    "interaction": re.compile(r"contact|riding|driving|driver|relation|above|on top", re.I),
    "agentic": re.compile(r"agent|contact sheet|reference|revision|inspect", re.I),
}


def _spans(text: str, term: str) -> list[tuple[int, int]]:
    return [
        (match.start(), match.end()) for match in re.finditer(rf"\b{re.escape(term)}\b", text, re.I)
    ]


def annotate_document(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record["text"])
    entities: list[dict[str, Any]] = []
    for label, terms in ENTITY_PATTERNS.items():
        for term in terms:
            for start, end in _spans(text, term):
                entities.append(
                    {"label": label, "text": text[start:end], "start": start, "end": end}
                )
    relations = [name for name, pattern in RELATION_PATTERNS.items() if pattern.search(text)]
    categories = [name for name, pattern in CATEGORY_PATTERNS.items() if pattern.search(text)]
    payload = {
        "source": record["source_id"],
        "categories": categories,
        "relations": relations,
    }
    idea_id = "idea:" + content_hash(payload)[7:19]
    return {
        "annotation_id": f"ann:{record['source_id']}",
        "source_id": record["source_id"],
        "idea_id": idea_id,
        "category": categories[0] if categories else "other",
        "categories": categories,
        "text_hash": content_hash(text),
        "entities": entities,
        "relations": relations,
        "requirement_links": [],
        "confidence": 0.55,
        "review_status": "machine-proposed",
        "pipeline_version": "0.1.0",
        "created_at": utc_now_iso(),
    }


def corpus_summary(annotations: list[dict[str, Any]]) -> dict[str, Any]:
    entity_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    for annotation in annotations:
        entity_counts.update(entity["label"] for entity in annotation["entities"])
        category_counts.update(annotation.get("categories", []))
        relation_counts.update(annotation.get("relations", []))
    return {
        "documents": len(annotations),
        "entity_counts": dict(sorted(entity_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "relation_counts": dict(sorted(relation_counts.items())),
        "unmapped_ideas": sum(
            not annotation.get("requirement_links") for annotation in annotations
        ),
    }
