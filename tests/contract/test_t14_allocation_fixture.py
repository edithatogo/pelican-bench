"""Combinatorial experiments only: no asset access, human ratings or actual assignment IDs."""

from collections import Counter
from dataclasses import replace
from itertools import combinations
from random import Random

import pytest
from t14_allocation_fixture import (
    Event,
    add_repeats,
    coverage,
    make_wave,
    presentation_budget,
    validate_wave,
)

pytestmark = pytest.mark.contract


@pytest.mark.parametrize("seed", range(32))
def test_complete_wave(seed: int) -> None:
    wave = make_wave(seed)
    validate_wave(wave)
    assert wave == make_wave(seed)
    assert Counter(coverage(wave).values()) == {3: 96}
    assert sum(map(len, wave.values())) == 312
    for participant, events in wave.items():
        base = {event.episode for event in events if not event.repeat}
        assert len(base) == 24
        assert sum(scene >= 18 for scene, _ in base) == 6
        assert Counter(variant for _, variant in base) == {0: 6, 1: 6, 2: 6, 3: 6}
        assert sorted(Counter(v for s, v in base if s >= 18).values()) == [1, 1, 2, 2]
        assert sorted(Counter(v for s, v in base if s < 18).values()) == [4, 4, 5, 5]
        for other in range(participant):
            shared = base & {e.episode for e in wave[other] if not e.repeat}
            assert len(shared) == (0 if participant // 4 == other // 4 else 6)
            if shared:
                assert sum(scene >= 18 for scene, _ in shared) in {1, 2}
                assert sum(scene < 18 for scene, _ in shared) in {4, 5}


def test_seed_changes_order_not_allocation() -> None:
    first, second = make_wave(0), make_wave(1)
    assert first != second
    for participant in first:
        assert {e.episode for e in first[participant]} == {e.episode for e in second[participant]}


@pytest.mark.parametrize("held_first", [False, True])
def test_extreme_ordering_still_has_spaced_repeats(held_first: bool) -> None:
    scenes = list(range(24))
    if held_first:
        scenes.reverse()
    base = [Event(scene, 0) for scene in scenes]
    original = base.copy()
    events = add_repeats(base, Random(0))
    assert base == original
    assert Counter(e.episode for e in events if not e.repeat) == Counter(e.episode for e in base)
    repeats = [e for e in events if e.repeat]
    assert len(repeats) == 2
    assert {e.scene >= 18 for e in repeats} == {False, True}
    for repeat in repeats:
        origin = next(
            i for i, e in enumerate(events) if not e.repeat and e.episode == repeat.episode
        )
        assert events.index(repeat) - origin - 1 >= 8


@pytest.mark.parametrize(
    "removed,expected",
    [
        ({0}, {2: 24, 3: 72}),
        ({0, 1}, {2: 48, 3: 48}),
        ({0, 4}, {1: 6, 2: 36, 3: 54}),
        ({0, 1, 2, 3}, {2: 96}),
        (set(range(12)), {0: 96}),
    ],
)
def test_dropout_keeps_denominators(removed: set[int], expected: dict[int, int]) -> None:
    wave = make_wave(0)
    remaining = {p: events for p, events in wave.items() if p not in removed}
    assert Counter(coverage(remaining).values()) == expected
    assert len(remaining) == 12 - len(removed)
    with pytest.raises(ValueError, match="enrollment"):
        validate_wave(remaining)


def test_zero_coverage_and_graph_connectivity() -> None:
    wave = make_wave(0)
    target = (0, 0)
    raters = {p for p, events in wave.items() if any(e.episode == target for e in events)}
    assert len(raters) == 3
    assert coverage({p: rows for p, rows in wave.items() if p not in raters})[target] == 0
    for held in [False, True]:
        edges = {
            p: {
                q
                for q in wave
                if p != q
                and (
                    {e.episode for e in wave[p] if not e.repeat and (e.scene >= 18) == held}
                    & {e.episode for e in wave[q] if not e.repeat and (e.scene >= 18) == held}
                )
            }
            for p in wave
        }
        reached = {0}
        for _ in wave:
            reached |= set().union(*(edges[p] for p in reached))
        assert reached == set(wave)


@pytest.mark.parametrize(
    "mutation", ["missing", "foreign", "variant", "spacing", "identity", "split"]
)
def test_malformed_wave_fails(mutation: str) -> None:
    wave = make_wave(0)
    rows = list(wave[0])
    if mutation == "missing":
        rows.pop()
    elif mutation == "foreign":
        rows[0] = replace(rows[0], scene=24)
    elif mutation == "variant":
        rows[0] = replace(rows[0], variant=4)
    else:
        repeat_index = next(i for i, e in enumerate(rows) if e.repeat)
        repeated = rows[repeat_index]
        if mutation == "spacing":
            rows.pop(repeat_index)
            origin = next(i for i, e in enumerate(rows) if e.episode == repeated.episode)
            rows.insert(origin + 1, repeated)
        elif mutation == "identity":
            rows[repeat_index] = replace(repeated, variant=(repeated.variant + 1) % 4)
        else:
            other = next(e for e in rows if e.repeat and e != repeated)
            rows[repeat_index] = other
    wave[0] = tuple(rows)
    with pytest.raises(ValueError):
        validate_wave(wave)


def test_integer_modulo_four_is_not_gf4() -> None:
    wave = make_wave(0)
    # Preserve per-scene 3-rater coverage while breaking planned pairwise overlap.
    for p, events in wave.items():
        wave[p] = tuple(replace(e, variant=(p % 4 + (p // 4) * (e.scene % 4)) % 4) for e in events)
    assert Counter(coverage(wave).values()) == {3: 96}
    with pytest.raises(ValueError, match="overlap"):
        validate_wave(wave)


def test_all_single_and_double_dropouts() -> None:
    wave = make_wave(0)
    for removed in [*combinations(wave, 1), *combinations(wave, 2)]:
        remaining = {p: rows for p, rows in wave.items() if p not in removed}
        assert sum(coverage(remaining).values()) == len(remaining) * 24
        assert len(coverage(remaining)) == 96


def test_budget_and_invalid_inputs() -> None:
    assert presentation_budget((0, 0, 0)) == 29
    assert presentation_budget((1, 1, 1)) == 32
    assert 12 * presentation_budget((0, 0, 0)) == 348
    assert 12 * presentation_budget((1, 1, 1)) == 384
    for retries in [(2, 0, 0), (-1, 0, 0), (0, 0), (True, 0, 0)]:
        with pytest.raises(ValueError):
            presentation_budget(retries)
    for seed in [-1, True, "D044"]:
        with pytest.raises(ValueError):
            make_wave(seed)  # type: ignore[arg-type]


def test_enrollment_overflow_and_invalid_base() -> None:
    wave = make_wave(0)
    wave[12] = wave[0]
    with pytest.raises(ValueError, match="enrollment"):
        validate_wave(wave)
    with pytest.raises(ValueError, match="base-scenes"):
        add_repeats([Event(0, 0)] * 24, Random(0))


def test_zero_multiplier_rejected_for_participant_imbalance() -> None:
    wave = make_wave(0)
    # XORing each variant with the scene coordinate preserves overlap but makes
    # the first group's variant constant, which this prospective toy design rejects.
    for p, events in wave.items():
        wave[p] = tuple(replace(e, variant=e.variant ^ (e.scene % 4)) for e in events)
    with pytest.raises(ValueError, match="participant-variant-balance"):
        validate_wave(wave)
