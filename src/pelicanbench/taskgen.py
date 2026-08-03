"""Deterministic generation of compositional benchmark scenarios and prompts."""

from __future__ import annotations

import itertools
import random
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .io import content_hash, read_json
from .models import BenchmarkTask, EntitySpec, RelationSpec

HERITAGE_PROMPT = "Generate an SVG of a pelican riding a bicycle"


def _stable_id(prefix: str, payload: Any, *, length: int = 20) -> str:
    return f"{prefix}:" + content_hash(payload).split(":", 1)[1][:length]


def load_grammar(path: str | Path) -> dict[str, Any]:
    grammar = read_json(path)
    if not isinstance(grammar, dict):
        raise TypeError("task grammar must be an object")
    validate_grammar(grammar)
    return grammar


def validate_grammar(grammar: dict[str, Any]) -> None:
    if "version" not in grammar:
        raise ValueError("grammar version is required")
    for key in ("animals", "mobile_objects", "relations"):
        if not isinstance(grammar.get(key), list) or not grammar[key]:
            raise ValueError(f"grammar requires {key}")
        identifiers = [str(item.get("id", "")) for item in grammar[key]]
        if any(not item for item in identifiers) or len(identifiers) != len(set(identifiers)):
            raise ValueError(f"{key} identifiers must be present and unique")

    relation_ids = {str(item["id"]) for item in grammar["relations"]}
    for animal in grammar["animals"]:
        unknown = set(animal.get("interaction_modes", ())) - relation_ids
        if unknown:
            raise ValueError(
                f"animal {animal['id']} has unknown interaction modes: {sorted(unknown)}"
            )
    for mobile_object in grammar["mobile_objects"]:
        unknown = set(mobile_object.get("interaction_modes", ())) - relation_ids
        if unknown:
            raise ValueError(
                f"mobile object {mobile_object['id']} has unknown interaction modes: {sorted(unknown)}"
            )
        if "interface_class" not in mobile_object:
            raise ValueError(f"mobile object {mobile_object['id']} requires interface_class")


def _compatible(
    animal: dict[str, Any],
    mobile_object: dict[str, Any],
    grammar: dict[str, Any],
) -> list[dict[str, Any]]:
    modes = set(animal.get("interaction_modes", ())) & set(
        mobile_object.get("interaction_modes", ())
    )
    output: list[dict[str, Any]] = []
    for relation in grammar["relations"]:
        if relation["id"] not in modes:
            continue
        allowed_classes = set(relation.get("allowed_object_classes", ()))
        if allowed_classes and mobile_object.get("class") not in allowed_classes:
            continue
        allowed_interfaces = set(relation.get("allowed_interface_classes", ()))
        object_interfaces = set(mobile_object.get("interface_classes", ()))
        if not object_interfaces and mobile_object.get("interface_class"):
            object_interfaces = {str(mobile_object["interface_class"])}
        if allowed_interfaces and not (allowed_interfaces & object_interfaces):
            continue
        output.append(relation)
    return output


def _entity(value: dict[str, Any], prefix: str) -> EntitySpec:
    return EntitySpec(
        id=str(value["id"]),
        label=str(value.get("label", value["id"])),
        ontology_ref=str(value.get("ontology_ref", f"{prefix}#{value['id']}")),
        required_features=tuple(map(str, value.get("required_features", ()))),
    )


def build_task(
    *,
    animal: dict[str, Any],
    mobile_object: dict[str, Any],
    relation: dict[str, Any],
    seed: int,
    release: str,
    grammar_version: str = "unknown",
    track: str = "compositional-svg",
    viewpoint: str = "side",
    style: str = "simple vector illustration",
    public: bool = True,
    prompt_template: str | None = None,
    prompt_variant: str = "canonical",
    references: tuple[str, ...] = (),
    condition: str = "one-shot-svg",
) -> BenchmarkTask:
    animal_entity = _entity(animal, "animal")
    object_entity = _entity(mobile_object, "mobile-object")
    template = prompt_template or relation.get(
        "prompt_template",
        (
            "Generate an SVG of a {animal} {relation_phrase} {mobile_object}, "
            "viewed from the {viewpoint}, in a {style} style."
        ),
    )
    prompt = str(template).format(
        animal=animal_entity.label,
        mobile_object=object_entity.label,
        relation=relation["id"],
        relation_phrase=relation.get("prompt_phrase", relation["id"].replace("_", " ")),
        viewpoint=viewpoint,
        style=style,
    )
    scenario_payload = {
        "grammar_version": grammar_version,
        "animal": animal_entity.id,
        "mobile_object": object_entity.id,
        "relation": relation["id"],
        "viewpoint": viewpoint,
    }
    scenario_id = _stable_id("scenario", scenario_payload)
    prompt_id = _stable_id(
        "prompt",
        {"scenario_id": scenario_id, "prompt": prompt, "variant": prompt_variant},
    )
    condition_id = _stable_id(
        "condition",
        {"track": track, "condition": condition, "references": references},
    )
    task_id = _stable_id(
        "pb",
        {
            "release": release,
            "scenario_id": scenario_id,
            "prompt_id": prompt_id,
            "condition_id": condition_id,
        },
        length=16,
    )

    anthropomorphism = int(animal.get("anthropomorphic_adaptation", 1))
    difficulty = (
        1
        + (viewpoint not in {"side", "profile"})
        + (relation["id"] not in {"rides_on", "passenger_in"})
        + (len(animal_entity.required_features) + len(object_entity.required_features) >= 10)
        + (style not in {"simple vector illustration", "flat icon"})
        + (anthropomorphism >= 3)
    )
    metadata = {
        "grammar_relation": relation["id"],
        "grammar_version": grammar_version,
        "object_class": mobile_object.get("class"),
        "animal_class": animal.get("class"),
        "body_plan": animal.get("body_plan"),
        "interface_class": mobile_object.get("interface_class"),
        "affordances": mobile_object.get("affordances", {}),
        "required_contacts": relation.get("required_contacts", []),
        "prompt_variant": prompt_variant,
        "design_seed": seed,
        "identity_contract": "scenario/prompt/condition independent of trial seed",
    }
    return BenchmarkTask(
        task_id=task_id,
        scenario_id=scenario_id,
        prompt_id=prompt_id,
        condition_id=condition_id,
        benchmark_release=release,
        track=track,  # type: ignore[arg-type]
        prompt=prompt,
        animal=animal_entity,
        mobile_object=object_entity,
        relations=(
            RelationSpec(
                predicate=str(relation["id"]),
                subject=animal_entity.id,
                object=object_entity.id,
            ),
        ),
        viewpoint=viewpoint,
        style=style,
        difficulty=min(int(difficulty), 5),
        seed=seed,
        public=public,
        references=references,
        metadata=metadata,
    )


def heritage_task(*, release: str = "PB-2026.08", seed: int = 0) -> BenchmarkTask:
    scenario_id = "scenario:heritage-pelican-rides-bicycle-v1"
    prompt_id = "prompt:heritage-exact-v1"
    condition_id = "condition:one-shot-svg-v1"
    return BenchmarkTask(
        task_id="pb:heritage-pelican-bike-v1",
        scenario_id=scenario_id,
        prompt_id=prompt_id,
        condition_id=condition_id,
        benchmark_release=release,
        track="heritage-svg",
        prompt=HERITAGE_PROMPT,
        animal=EntitySpec(
            id="pelican",
            label="pelican",
            ontology_ref="pelican#pelican",
            required_features=("bill", "gular-pouch", "wing", "webbed-foot"),
        ),
        mobile_object=EntitySpec(
            id="bicycle",
            label="bicycle",
            ontology_ref="bicycle#bicycle",
            required_features=("front-wheel", "rear-wheel", "frame", "handlebar", "pedal"),
        ),
        relations=(RelationSpec(predicate="rides_on", subject="pelican", object="bicycle"),),
        viewpoint="unspecified",
        style="unspecified",
        difficulty=2,
        seed=seed,
        public=True,
        metadata={
            "heritage_anchor": True,
            "exact_prompt": True,
            "design_seed": seed,
            "identity_contract": "stable heritage task; trial seeds are external",
        },
    )


def _candidate_designs(grammar: dict[str, Any]) -> list[tuple[dict[str, Any], ...]]:
    output: list[tuple[dict[str, Any], ...]] = []
    viewpoints = grammar.get("viewpoints", ["side"])
    styles = grammar.get("styles", ["simple vector illustration"])
    for animal, mobile_object in itertools.product(grammar["animals"], grammar["mobile_objects"]):
        for relation in _compatible(animal, mobile_object, grammar):
            for viewpoint, style in itertools.product(viewpoints, styles):
                output.append((animal, mobile_object, relation, viewpoint, style))
    return output


def generate_tasks(
    grammar: dict[str, Any],
    *,
    count: int,
    seed: int,
    release: str = "PB-2026.08",
    public: bool = True,
    include_heritage: bool = True,
) -> list[BenchmarkTask]:
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)  # nosec B311
    candidates = _candidate_designs(grammar)
    if not candidates:
        raise ValueError("grammar has no compatible combinations")
    rng.shuffle(candidates)
    capacity = len(candidates) + int(include_heritage)
    if count > capacity:
        raise ValueError(f"requested {count} unique tasks but grammar provides {capacity}")

    output: list[BenchmarkTask] = []
    if include_heritage:
        output.append(heritage_task(release=release, seed=seed))
    for animal, mobile_object, relation, viewpoint, style in candidates:
        if len(output) >= count:
            break
        design_seed = rng.randrange(0, 2**31)
        output.append(
            build_task(
                animal=animal,
                mobile_object=mobile_object,
                relation=relation,
                seed=design_seed,
                release=release,
                grammar_version=str(grammar["version"]),
                viewpoint=str(viewpoint),
                style=str(style),
                public=public,
            )
        )
    if len({task.task_id for task in output}) != len(output):
        raise AssertionError("task generation produced duplicate stable identities")
    return output


def generate_design_tasks(
    grammar: dict[str, Any],
    design: dict[str, Any],
    *,
    seed: int,
) -> list[BenchmarkTask]:
    """Generate a prespecified pilot from affordance-stratified design entries."""

    animals = {item["id"]: item for item in grammar["animals"]}
    objects = {item["id"]: item for item in grammar["mobile_objects"]}
    relations = {item["id"]: item for item in grammar["relations"]}
    rng = random.Random(seed)  # nosec B311
    output: list[BenchmarkTask] = []
    if design.get("include_heritage", True):
        output.append(heritage_task(release=str(design["release"]), seed=seed))
    for entry in design.get("scenarios", []):
        animal = animals[str(entry["animal"])]
        mobile_object = objects[str(entry["mobile_object"])]
        relation = relations[str(entry["relation"])]
        if relation not in _compatible(animal, mobile_object, grammar):
            raise ValueError(f"incompatible design entry: {entry}")
        templates = entry.get("prompt_templates", [None])
        for prompt_index, template in enumerate(templates):
            task = build_task(
                animal=animal,
                mobile_object=mobile_object,
                relation=relation,
                seed=rng.randrange(0, 2**31),
                release=str(design["release"]),
                grammar_version=str(grammar["version"]),
                viewpoint=str(entry.get("viewpoint", "side")),
                style=str(entry.get("style", "simple vector illustration")),
                public=bool(entry.get("public", True)),
                prompt_template=template,
                prompt_variant=f"{entry.get('id', 'design')}-p{prompt_index + 1}",
                condition=str(entry.get("condition", "one-shot-svg")),
            )
            output.append(
                task.model_copy(
                    update={
                        "metadata": {
                            **task.metadata,
                            "design_scenario_id": str(entry.get("id", "")),
                            "interface_stratum": str(entry.get("stratum", "")),
                        }
                    }
                )
            )
    if len({task.task_id for task in output}) != len(output):
        raise ValueError("pilot design contains duplicate task identities")
    return output


def full_factorial(
    grammar: dict[str, Any],
    *,
    release: str,
    seed: int,
    animals: Iterable[str] | None = None,
    mobile_objects: Iterable[str] | None = None,
) -> list[BenchmarkTask]:
    animal_filter = set(animals or ())
    object_filter = set(mobile_objects or ())
    output: list[BenchmarkTask] = []
    index = 0
    for animal in grammar["animals"]:
        if animal_filter and animal["id"] not in animal_filter:
            continue
        for mobile_object in grammar["mobile_objects"]:
            if object_filter and mobile_object["id"] not in object_filter:
                continue
            for relation in _compatible(animal, mobile_object, grammar):
                output.append(
                    build_task(
                        animal=animal,
                        mobile_object=mobile_object,
                        relation=relation,
                        seed=seed + index,
                        release=release,
                        grammar_version=str(grammar["version"]),
                    )
                )
                index += 1
    return output


def split_public_sealed(
    tasks: list[BenchmarkTask],
    *,
    sealed_fraction: float,
    seed: int,
) -> tuple[list[BenchmarkTask], list[BenchmarkTask]]:
    if not 0 < sealed_fraction < 1:
        raise ValueError("sealed_fraction must be between 0 and 1")
    heritage = [task for task in tasks if task.track == "heritage-svg"]
    rest = [task for task in tasks if task.track != "heritage-svg"]
    random.Random(seed).shuffle(rest)  # nosec B311
    count = max(1, round(len(rest) * sealed_fraction))
    sealed = [
        BenchmarkTask.model_validate({**task.model_dump(), "public": False})
        for task in rest[:count]
    ]
    return heritage + rest[count:], sealed


def task_set_commitment(tasks: Iterable[BenchmarkTask]) -> str:
    payload = sorted(
        (
            task.task_id,
            task.scenario_id,
            task.prompt_id,
            task.condition_id,
        )
        for task in tasks
    )
    return content_hash(payload)
