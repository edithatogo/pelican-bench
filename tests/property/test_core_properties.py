from __future__ import annotations

import importlib.util
import random

import pytest

from pelicanbench.io import canonical_json, content_hash
from pelicanbench.simulation import assert_deterministic_replay
from pelicanbench.taskgen import build_task

pytestmark = pytest.mark.property


def test_canonical_json_is_mapping_order_invariant() -> None:
    rng = random.Random(20260802)
    keys = [f"k{index}" for index in range(20)]
    baseline = {key: index for index, key in enumerate(keys)}
    expected = content_hash(baseline)
    for _ in range(100):
        rng.shuffle(keys)
        value = {key: baseline[key] for key in keys}
        assert content_hash(value) == expected
        assert canonical_json(value) == canonical_json(baseline)


def test_task_identity_is_independent_of_design_seed(grammar) -> None:
    animal = next(item for item in grammar["animals"] if item["id"] == "pelican")
    mobile_object = next(item for item in grammar["mobile_objects"] if item["id"] == "bicycle")
    relation = next(item for item in grammar["relations"] if item["id"] == "rides_on")
    first = build_task(
        animal=animal, mobile_object=mobile_object, relation=relation, seed=1, release="R"
    )
    second = build_task(
        animal=animal, mobile_object=mobile_object, relation=relation, seed=2, release="R"
    )
    assert first.task_id == second.task_id
    assert first.seed != second.seed


def test_random_valid_action_sequences_replay_deterministically() -> None:
    rng = random.Random(42)
    actions = []
    for index in range(25):
        actions.append(
            {
                "type": "add",
                "id": f"e{index}",
                "element": {
                    "tag": "circle",
                    "attributes": {
                        "cx": rng.randrange(0, 100),
                        "cy": rng.randrange(0, 100),
                        "r": rng.randrange(1, 10),
                    },
                },
            }
        )
    receipt = assert_deterministic_replay(actions, seed=42)
    assert len(receipt.steps) == len(actions)


@pytest.mark.skipif(
    importlib.util.find_spec("hypothesis") is None, reason="Hypothesis is a mandatory CI dependency"
)
def test_hypothesis_content_hash_property() -> None:
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=50, derandomize=True)
    @given(st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=20))
    def check(value: dict[str, int]) -> None:
        assert content_hash(value) == content_hash(dict(reversed(list(value.items()))))

    check()
