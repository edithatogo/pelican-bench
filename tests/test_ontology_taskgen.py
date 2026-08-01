from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.ontology import (
    Ontology,
    evaluate_competency_cases,
    abstract_specialised_ontology,
    compose_scene,
    merge_ontologies,
)
from pelicanbench.taskgen import (
    HERITAGE_PROMPT,
    full_factorial,
    generate_design_tasks,
    generate_tasks,
    heritage_task,
    split_public_sealed,
    task_set_commitment,
    validate_grammar,
)


def test_all_ontologies_load(root: Path):
    loaded = [Ontology.load(path) for path in sorted((root / "benchmark/ontologies").glob("*.json"))]
    assert len(loaded) == 7
    assert all(item.version in {"0.1.0", "0.2.0"} for item in loaded)
    assert all(item.to_jsonld()["@type"] == "pb:Ontology" for item in loaded)


def test_animal_inheritance_and_features(root: Path):
    ontology = Ontology.load(root / "benchmark/ontologies/animal.json")
    assert ontology.is_a("pelican", "animal")
    assert "bird" in ontology.ancestors("pelican")
    features = ontology.required_features("pelican")
    assert {"body", "wing", "elongated-bill", "gular-pouch"} <= set(features)
    with pytest.raises(KeyError):
        ontology.ancestors("dragon")


def test_cycle_detection():
    with pytest.raises(ValueError, match="cycle"):
        Ontology.from_dict(
            {
                "id": "cycle",
                "version": "1",
                "concepts": [{"id": "a", "parent": "b"}, {"id": "b", "parent": "a"}],
                "relations": [],
            }
        )


def test_missing_parent_and_inverse():
    with pytest.raises(ValueError, match="unknown parent"):
        Ontology.from_dict({"id": "x", "version": "1", "concepts": [{"id": "a", "parent": "z"}]})
    with pytest.raises(ValueError, match="unknown inverse"):
        Ontology.from_dict(
            {
                "id": "x",
                "version": "1",
                "concepts": [{"id": "a"}],
                "relations": [{"id": "r", "inverse": "missing"}],
            }
        )


def test_merge_and_conflict():
    a = Ontology.from_dict({"id": "a", "version": "1", "concepts": [{"id": "root"}]})
    b = Ontology.from_dict({"id": "b", "version": "1", "concepts": [{"id": "child"}]})
    merged = merge_ontologies([a, b], ontology_id="m", version="1")
    assert set(merged.concepts) == {"root", "child"}
    conflict = Ontology.from_dict(
        {"id": "c", "version": "1", "concepts": [{"id": "root", "label": "other"}]}
    )
    with pytest.raises(ValueError, match="conflicting concept"):
        merge_ontologies([a, conflict], ontology_id="m", version="1")


def test_compose_bicycle_and_tuktuk(root: Path):
    animal = Ontology.load(root / "benchmark/ontologies/animal.json")
    mobile = Ontology.load(root / "benchmark/ontologies/mobile-object.json")
    interface = Ontology.load(root / "benchmark/ontologies/interface.json")
    bike = compose_scene(animal, mobile, interface, animal_id="pelican", mobile_id="bicycle", relation_id="rides_on")
    assert bike["relation"] == "rides_on"
    tuktuk = compose_scene(animal, mobile, interface, animal_id="pelican", mobile_id="tuk-tuk", relation_id="drives")
    assert "driver-position" in tuktuk["required_object_features"]
    with pytest.raises(ValueError):
        compose_scene(animal, mobile, interface, animal_id="pelican", mobile_id="tuk-tuk", relation_id="rides_on")


def test_abstraction_candidate():
    candidate = abstract_specialised_ontology(
        {"concepts": [{"id": "pelican"}, {"id": "bill", "parent": "pelican"}]},
        new_id="animal-candidate",
        parent_mapping={"pelican": "animal", "bill": "feeding-appendage"},
    )
    assert candidate["status"] == "candidate-human-review-required"
    assert {item["id"] for item in candidate["concepts"]} == {"animal", "feeding-appendage"}


def test_grammar_and_generation(grammar):
    validate_grammar(grammar)
    tasks = generate_tasks(grammar, count=25, seed=42)
    assert len(tasks) == 25
    assert tasks[0].prompt == HERITAGE_PROMPT
    assert len({task.task_id for task in tasks}) == 25
    assert any(task.mobile_object.id == "tuk-tuk" for task in generate_tasks(grammar, count=100, seed=1))


def test_generation_is_deterministic(grammar):
    first = [item.model_dump() for item in generate_tasks(grammar, count=12, seed=7)]
    second = [item.model_dump() for item in generate_tasks(grammar, count=12, seed=7)]
    assert first == second


def test_factorial_and_filters(grammar):
    tasks = full_factorial(grammar, release="PB", seed=1, animals=["pelican"], mobile_objects=["bicycle", "tuk-tuk"])
    assert {task.mobile_object.id for task in tasks} == {"bicycle", "tuk-tuk"}
    assert {task.relations[0].predicate for task in tasks} == {"rides_on", "operates", "drives", "passenger_in"}


def test_public_sealed_split(grammar):
    tasks = generate_tasks(grammar, count=20, seed=1)
    public, sealed = split_public_sealed(tasks, sealed_fraction=0.25, seed=2)
    assert len(public) + len(sealed) == 20
    assert any(task.track == "heritage-svg" for task in public)
    assert all(not task.public for task in sealed)
    with pytest.raises(ValueError):
        split_public_sealed(tasks, sealed_fraction=1, seed=1)


def test_bad_grammar():
    with pytest.raises(ValueError):
        validate_grammar({})
    with pytest.raises(ValueError):
        validate_grammar({"version": "1", "animals": [{"id": "x"}, {"id": "x"}], "mobile_objects": [{"id": "o"}], "relations": [{"id": "r"}]})


def test_heritage_task():
    task = heritage_task(seed=5)
    assert task.seed == 5
    assert heritage_task(seed=99).task_id == task.task_id
    assert heritage_task(seed=99).scenario_id == task.scenario_id
    assert task.metadata["exact_prompt"] is True
    assert task.track == "heritage-svg"


def test_task_identity_is_independent_of_design_seed(grammar):
    first = generate_tasks(grammar, count=8, seed=11)
    repeated = generate_tasks(grammar, count=8, seed=11)
    assert [item.task_id for item in first] == [item.task_id for item in repeated]
    heritage_a = heritage_task(seed=1)
    heritage_b = heritage_task(seed=999)
    assert heritage_a.task_id == heritage_b.task_id
    assert heritage_a.scenario_id == heritage_b.scenario_id
    assert heritage_a.prompt_id == heritage_b.prompt_id
    assert heritage_a.condition_id == heritage_b.condition_id
    assert heritage_a.seed != heritage_b.seed


def test_prespecified_pilot_and_commitment(root: Path, grammar):
    design = json.loads((root / "benchmark/tasks/v1-pilot-design.json").read_text())
    tasks = generate_design_tasks(grammar, design, seed=design["seed"])
    commitment = json.loads(
        (root / "benchmark/tasks/v1-pilot-commitment.json").read_text()
    )
    assert len(tasks) == 33
    assert len({task.scenario_id for task in tasks}) == 17
    assert task_set_commitment(tasks) == commitment["commitment"]
    assert {task.metadata.get("interface_stratum") for task in tasks if task.track != "heritage-svg"} == {
        "straddle-and-propel",
        "stand-and-balance",
        "sit-inside-and-control",
        "occupy-and-propel",
    }


def test_ontology_competency_cases(root: Path):
    cases = json.loads(
        (root / "benchmark/ontology-tests/competency-cases.json").read_text()
    )["cases"]
    results = evaluate_competency_cases(
        Ontology.load(root / "benchmark/ontologies/animal.json"),
        Ontology.load(root / "benchmark/ontologies/mobile-object.json"),
        Ontology.load(root / "benchmark/ontologies/interface.json"),
        cases,
    )
    assert results
    assert all(item.passed for item in results)
