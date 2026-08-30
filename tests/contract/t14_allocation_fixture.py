"""Pure toy allocation model. No files, production IDs, assets, ratings or collection."""

from collections import Counter
from dataclasses import dataclass, replace
from itertools import combinations
from random import Random


@dataclass(frozen=True)
class Event:
    """Integer labels belong only to this synthetic universe, not T14 source mappings."""

    scene: int
    variant: int
    repeat: bool = False

    @property
    def episode(self) -> tuple[int, int]:
        return self.scene, self.variant


def add_repeats(base: list[Event], rng: Random) -> tuple[Event, ...]:
    """Construct feasibility, not a uniformly random or approved blinded schedule."""
    rows = base.copy()
    if len(rows) != 24 or {e.scene for e in rows} != set(range(24)) or any(e.repeat for e in rows):
        raise ValueError("base-scenes")
    # Select each repeat origin within the first 16 bases so even end insertion has
    # at least eight intervening presentations. Repair a late-only partition first.
    for held in (False, True):
        if not any((e.scene >= 18) == held for e in rows[:16]):
            later = next(i for i, e in enumerate(rows) if (e.scene >= 18) == held)
            early = rng.randrange(16)
            rows[early], rows[later] = rows[later], rows[early]
    origins = [
        rng.choice([e for e in rows[:16] if (e.scene >= 18) == held]) for held in (False, True)
    ]
    rng.shuffle(origins)
    for origin in origins:
        position = rows.index(origin)
        insertion = rng.randrange(position + 9, len(rows) + 1)
        rows.insert(insertion, replace(origin, repeat=True))
    return tuple(rows)


def make_wave(seed: int) -> dict[int, tuple[Event, ...]]:
    """Fixed GF(4) balance; the explicit toy seed changes order/repeat selection only."""
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("toy-seed")
    rng = Random(seed)
    # Nonzero multipliers 1, 2, 3 in GF(4), polynomial x^2 + x + 1.
    # Unlike multiplier zero, each gives every participant six bases per variant.
    products = ((0, 1, 2, 3), (0, 2, 3, 1), (0, 3, 1, 2))
    wave: dict[int, tuple[Event, ...]] = {}
    for participant in range(12):
        group, offset = divmod(participant, 4)
        base = [Event(scene, offset ^ products[group][scene % 4]) for scene in range(24)]
        rng.shuffle(base)
        wave[participant] = add_repeats(base, rng)
    return wave


def coverage(wave: dict[int, tuple[Event, ...]]) -> Counter[tuple[int, int]]:
    """Coverage of planned toy assignments only, retaining all 96 zero-capable cells."""
    result = Counter({(scene, variant): 0 for scene in range(24) for variant in range(4)})
    result.update(e.episode for rows in wave.values() for e in rows if not e.repeat)
    return result


def validate_wave(wave: dict[int, tuple[Event, ...]]) -> None:
    """Reject structurally wrong complete toy waves, never normalize malformed input."""
    if set(wave) != set(range(12)) or any(type(p) is not int for p in wave):
        raise ValueError("enrollment")
    bases: dict[int, set[tuple[int, int]]] = {}
    for participant, rows in wave.items():
        if len(rows) != 26:
            raise ValueError("presentation-count")
        if any(
            type(e.scene) is not int
            or type(e.variant) is not int
            or type(e.repeat) is not bool
            or not 0 <= e.scene < 24
            or not 0 <= e.variant < 4
            for e in rows
        ):
            raise ValueError("toy-domain")
        base = [e for e in rows if not e.repeat]
        repeats = [e for e in rows if e.repeat]
        if len(base) != 24 or {e.scene for e in base} != set(range(24)):
            raise ValueError("base-scenes")
        if len(repeats) != 2 or {e.scene >= 18 for e in repeats} != {False, True}:
            raise ValueError("repeat-partitions")
        bases[participant] = {e.episode for e in base}
        for repeat in repeats:
            if repeat.episode not in bases[participant]:
                raise ValueError("repeat-identity")
            origin_index = next(
                i for i, e in enumerate(rows) if not e.repeat and e.episode == repeat.episode
            )
            if rows.index(repeat) - origin_index - 1 < 8:
                raise ValueError("repeat-spacing")
    if Counter(coverage(wave).values()) != {3: 96}:
        raise ValueError("episode-coverage")
    for episode in coverage(wave):
        groups = {p // 4 for p in wave if episode in bases[p]}
        if groups != {0, 1, 2}:
            raise ValueError("group-coverage")
    for p, q in combinations(wave, 2):
        shared = bases[p] & bases[q]
        expected = 0 if p // 4 == q // 4 else 6
        if len(shared) != expected:
            raise ValueError("overlap")
        if shared and sum(scene >= 18 for scene, _ in shared) not in {1, 2}:
            raise ValueError("partition-overlap")
    for base in bases.values():
        if Counter(variant for _, variant in base) != {0: 6, 1: 6, 2: 6, 3: 6}:
            raise ValueError("participant-variant-balance")


def presentation_budget(practice_retries: tuple[int, ...]) -> int:
    """Upper workload per toy enrollee; not permission to recruit or replace anyone."""
    if len(practice_retries) != 3 or any(
        type(n) is not int or n not in {0, 1} for n in practice_retries
    ):
        raise ValueError("practice-retry-cap")
    return 26 + 3 + sum(practice_retries)
