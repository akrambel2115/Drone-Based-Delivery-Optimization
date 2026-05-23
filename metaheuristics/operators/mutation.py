"""Mutation operators on giant-tour permutations.

Mutation is applied to the GA chromosome (a permutation of customer IDs)
to inject diversity. Each operator preserves the permutation invariant
so that the result remains a valid input for the Split decoder.
"""

from __future__ import annotations

import random
from typing import Sequence


def swap_mutation(chromosome: Sequence[int], rng: random.Random) -> list[int]:
    """Swap two random positions."""
    out = list(chromosome)
    if len(out) < 2:
        return out
    i, j = rng.sample(range(len(out)), 2)
    out[i], out[j] = out[j], out[i]
    return out


def inversion_mutation(chromosome: Sequence[int], rng: random.Random) -> list[int]:
    """Reverse a random sub-segment of the chromosome.

    Equivalent to 2-opt on the giant tour. With Split this is a very
    effective diversification because the route boundaries are
    automatically re-optimised after the inversion.
    """
    out = list(chromosome)
    n = len(out)
    if n < 2:
        return out
    i, j = sorted(rng.sample(range(n), 2))
    out[i : j + 1] = list(reversed(out[i : j + 1]))
    return out


def relocate_mutation(chromosome: Sequence[int], rng: random.Random) -> list[int]:
    """Take a customer out and re-insert it at a different position."""
    out = list(chromosome)
    n = len(out)
    if n < 2:
        return out
    source = rng.randrange(n)
    customer = out.pop(source)
    target = rng.randrange(len(out) + 1)
    out.insert(target, customer)
    return out
