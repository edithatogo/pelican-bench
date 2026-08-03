"""Transparent empirical prompt annotation for benchmark-design audits.

The module intentionally uses deterministic lexicons and rules rather than presenting a
large language model as validated NER. It produces auditable spans, canonical entities,
relations, and aggregate coverage reports that can later be compared with a manually
annotated gold corpus.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from .models import BenchmarkTask

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])")

ANIMAL_ALIASES: dict[str, str] = {
    name: name
    for name in (
        "antelope",
        "cat",
        "dog",
        "flamingo",
        "heron",
        "octopus",
        "otter",
        "pelican",
        "raccoon",
        "whale",
    )
}
MOBILE_OBJECT_ALIASES: dict[str, str] = {
    "bicycle": "bicycle",
    "bike": "bicycle",
    "boat": "boat",
    "canoe": "canoe",
    "electric scooter": "electric-scooter",
    "go-kart": "go-kart",
    "go kart": "go-kart",
    "kayak": "kayak",
    "plane": "plane",
    "aircraft": "plane",
    "scooter": "electric-scooter",
    "skateboard": "skateboard",
    "tuk-tuk": "tuk-tuk",
    "tuk tuk": "tuk-tuk",
    "unicycle": "unicycle",
}
RELATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("rides_on", re.compile(r"\b(?:riding|rides?|astride)\b", re.IGNORECASE)),
    ("drives", re.compile(r"\b(?:driving|drives?)\b", re.IGNORECASE)),
    ("paddles", re.compile(r"\b(?:paddling|paddles?)\b", re.IGNORECASE)),
    ("operates", re.compile(r"\b(?:operating|operates?)\b", re.IGNORECASE)),
    ("aboard", re.compile(r"\bon\s+an?\s+(?:plane|boat|aircraft)\b", re.IGNORECASE)),
    ("passenger_in", re.compile(r"\b(?:passenger|sitting|seated)\s+in\b", re.IGNORECASE)),
)
STYLE_PATTERNS: dict[str, re.Pattern[str]] = {
    "flat": re.compile(r"\bflat(?:\s+vector)?\b", re.IGNORECASE),
    "simple-vector": re.compile(r"\bsimple\s+vector\b", re.IGNORECASE),
    "photorealistic": re.compile(r"\bphotoreal(?:istic)?\b", re.IGNORECASE),
    "line-art": re.compile(r"\bline[ -]?art\b", re.IGNORECASE),
}
VIEWPOINT_PATTERNS: dict[str, re.Pattern[str]] = {
    "side": re.compile(
        r"\b(?:side|profile)\s+(?:view|on)\b|\bviewed\s+from\s+the\s+side\b", re.IGNORECASE
    ),
    "front": re.compile(r"\bfront(?:al)?\s+view\b|\bviewed\s+from\s+the\s+front\b", re.IGNORECASE),
    "rear": re.compile(r"\brear\s+view\b|\bviewed\s+from\s+behind\b", re.IGNORECASE),
    "three-quarter": re.compile(r"\bthree[- ]quarter\b|\b3/4\s+view\b", re.IGNORECASE),
}


@dataclass(frozen=True, slots=True)
class PromptRecord:
    source_id: str
    record_id: str
    prompt: str
    language: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> PromptRecord:
        return cls(
            source_id=str(value["source_id"]),
            record_id=str(value["record_id"]),
            prompt=str(value.get("prompt", value.get("text", ""))),
            language=str(value.get("language", "en")),
            metadata=dict(value.get("metadata", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EntityMention:
    entity_type: str
    canonical_id: str
    surface: str
    start: int
    end: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PromptAnnotation:
    source_id: str
    record_id: str
    prompt: str
    language: str
    tokens: tuple[str, ...]
    mentions: tuple[EntityMention, ...]
    relations: tuple[str, ...]
    viewpoints: tuple[str, ...]
    styles: tuple[str, ...]
    numeric_constraints: tuple[str, ...]
    asks_for_svg: bool
    asks_for_animation: bool
    asks_for_editability: bool
    asks_for_text: bool
    compositional: bool
    awkward_or_adversarial: bool

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["mentions"] = [item.as_dict() for item in self.mentions]
        return value


def _mentions(prompt: str, aliases: Mapping[str, str], entity_type: str) -> list[EntityMention]:
    output: list[EntityMention] = []
    for surface, canonical in aliases.items():
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(surface)}(?![A-Za-z0-9])", re.IGNORECASE)
        for match in pattern.finditer(prompt):
            output.append(
                EntityMention(
                    entity_type=entity_type,
                    canonical_id=canonical,
                    surface=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
            )
    # Prefer the longest alias at the same start position and remove overlapping aliases.
    output.sort(
        key=lambda item: (item.start, -(item.end - item.start), item.entity_type, item.canonical_id)
    )
    retained: list[EntityMention] = []
    for item in output:
        if any(not (item.end <= prior.start or item.start >= prior.end) for prior in retained):
            continue
        retained.append(item)
    return retained


def annotate_prompt(record: PromptRecord | Mapping[str, Any]) -> PromptAnnotation:
    value = record if isinstance(record, PromptRecord) else PromptRecord.from_mapping(record)
    prompt = value.prompt
    animal_mentions = _mentions(prompt, ANIMAL_ALIASES, "animal")
    object_mentions = _mentions(prompt, MOBILE_OBJECT_ALIASES, "mobile_object")
    mentions = tuple(
        sorted((*animal_mentions, *object_mentions), key=lambda item: (item.start, item.end))
    )
    relations = tuple(relation for relation, pattern in RELATION_PATTERNS if pattern.search(prompt))
    # "on a plane/boat" is an aboard relation, not a generic ride relation.
    if (
        "aboard" in relations
        and "rides_on" in relations
        and not re.search(r"\briding\b", prompt, re.IGNORECASE)
    ):
        relations = tuple(item for item in relations if item != "rides_on")
    viewpoints = tuple(
        name for name, pattern in VIEWPOINT_PATTERNS.items() if pattern.search(prompt)
    )
    styles = tuple(name for name, pattern in STYLE_PATTERNS.items() if pattern.search(prompt))
    tokens = tuple(match.group(0).lower() for match in TOKEN_RE.finditer(prompt))
    numbers = tuple(match.group(0) for match in NUMBER_RE.finditer(prompt))
    lower = prompt.lower()
    compositional = bool(animal_mentions and object_mentions)
    return PromptAnnotation(
        source_id=value.source_id,
        record_id=value.record_id,
        prompt=prompt,
        language=value.language,
        tokens=tokens,
        mentions=mentions,
        relations=relations,
        viewpoints=viewpoints,
        styles=styles,
        numeric_constraints=numbers,
        asks_for_svg=bool(re.search(r"\bsvg\b", lower)),
        asks_for_animation=bool(re.search(r"\b(?:animate|animated|animation|motion)\b", lower)),
        asks_for_editability=bool(
            re.search(r"\b(?:editable|editability|layered|grouped)\b", lower)
        ),
        asks_for_text=bool(re.search(r"\b(?:caption|label|lettering|text)\b", lower)),
        compositional=compositional,
        awkward_or_adversarial=compositional,
    )


def annotate_prompt_corpus(
    records: Iterable[PromptRecord | Mapping[str, Any]],
) -> tuple[PromptAnnotation, ...]:
    annotations = tuple(annotate_prompt(record) for record in records)
    identifiers = [item.record_id for item in annotations]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("prompt record identifiers must be unique")
    return annotations


def empirical_nlp_report(
    annotations: Sequence[PromptAnnotation],
    *,
    evidence_status: str = "source-derived-rule-based-E2",
) -> dict[str, Any]:
    count = len(annotations)
    if count == 0:
        raise ValueError("at least one annotation is required")
    entities = Counter(
        mention.canonical_id for annotation in annotations for mention in annotation.mentions
    )
    relations = Counter(relation for annotation in annotations for relation in annotation.relations)
    viewpoints = Counter(
        viewpoint for annotation in annotations for viewpoint in annotation.viewpoints
    )
    styles = Counter(style for annotation in annotations for style in annotation.styles)
    languages = Counter(annotation.language for annotation in annotations)
    return {
        "schema_version": "1.0.0",
        "evidence_status": evidence_status,
        "records": count,
        "languages": dict(sorted(languages.items())),
        "entity_counts": dict(sorted(entities.items())),
        "relation_counts": dict(sorted(relations.items())),
        "viewpoint_counts": dict(sorted(viewpoints.items())),
        "style_counts": dict(sorted(styles.items())),
        "prompts_with_numeric_constraints": sum(
            bool(item.numeric_constraints) for item in annotations
        ),
        "svg_intent_share": sum(item.asks_for_svg for item in annotations) / count,
        "animation_share": sum(item.asks_for_animation for item in annotations) / count,
        "editability_share": sum(item.asks_for_editability for item in annotations) / count,
        "compositional_share": sum(item.compositional for item in annotations) / count,
        "awkward_or_adversarial_share": sum(item.awkward_or_adversarial for item in annotations)
        / count,
    }


def task_design_coverage(
    annotations: Sequence[PromptAnnotation],
    tasks: Sequence[BenchmarkTask],
    *,
    panel_id: str | None = None,
    evidence_status: str = "source-derived-rule-based-E2",
) -> dict[str, Any]:
    selected = [
        task for task in tasks if panel_id is None or str(task.metadata.get("panel_id")) == panel_id
    ]
    source_prompts = {item.prompt for item in annotations}
    task_prompts = {item.prompt for item in selected}
    source_animals = {
        mention.canonical_id
        for item in annotations
        for mention in item.mentions
        if mention.entity_type == "animal"
    }
    source_objects = {
        mention.canonical_id
        for item in annotations
        for mention in item.mentions
        if mention.entity_type == "mobile_object"
    }
    source_relations = {relation for item in annotations for relation in item.relations}
    represented_animals = {task.animal.id for task in selected}
    represented_objects = {
        MOBILE_OBJECT_ALIASES.get(task.mobile_object.id, task.mobile_object.id) for task in selected
    }
    matched_annotations = [item for item in annotations if item.prompt in task_prompts]
    represented_relations = {
        relation for item in matched_annotations for relation in item.relations
    }
    exact_matches = len(source_prompts & task_prompts)
    return {
        "schema_version": "1.0.0",
        "evidence_status": evidence_status,
        "source_records": len(annotations),
        "benchmark_tasks": len(selected),
        "exact_prompt_matches": exact_matches,
        "exact_prompt_coverage": exact_matches / len(source_prompts) if source_prompts else 0.0,
        "source_animals": sorted(source_animals),
        "source_mobile_objects": sorted(source_objects),
        "source_relations": sorted(source_relations),
        "represented_animals": sorted(represented_animals & source_animals),
        "represented_mobile_objects": sorted(represented_objects & source_objects),
        "benchmark_relations_from_prompt_nlp": sorted(represented_relations),
        "missing_animals": sorted(source_animals - represented_animals),
        "missing_mobile_objects": sorted(source_objects - represented_objects),
        "missing_relations": sorted(source_relations - represented_relations),
    }


__all__ = [
    "EntityMention",
    "PromptAnnotation",
    "PromptRecord",
    "annotate_prompt",
    "annotate_prompt_corpus",
    "empirical_nlp_report",
    "task_design_coverage",
]
