"""Crossover operators for the GA.

The chromosome is a giant-tour permutation of the ``N`` customer IDs.
Because crossover operates on the permutation (not the list-of-routes
representation), the offspring is always a valid permutation; feasibility
is enforced at decoding time by :func:`split_giant_tour`.

Currently implemented:

* :func:`order_crossover` (OX1) — the de-facto standard for permutation
  encodings. It preserves relative order from one parent and absolute
  positions from a segment of the other.
"""

from __future__ import annotations

import random
from typing import Sequence


def order_crossover(
    parent_a: Sequence[int],
    parent_b: Sequence[int],
    rng: random.Random,
) -> tuple[list[int], list[int]]:
    """OX1 ordered crossover producing two offspring permutations.

    Steps
    -----
    1. Pick two cut points ``i < j``.
    2. Copy ``parent_a[i:j]`` into ``child_a`` at the same positions.
    3. Fill the remaining positions of ``child_a`` with the customers of
       ``parent_b`` in their relative order, skipping already-placed
       customers and wrapping around at the end of ``parent_b``.
    4. Apply the symmetric construction to obtain ``child_b``.

    Both parents must be permutations of the same set of customer IDs.
    """
    n = len(parent_a)
    if n != len(parent_b):
        raise ValueError("Parents must have the same length")
    if n < 2:
        return list(parent_a), list(parent_b)

    cut1, cut2 = sorted(rng.sample(range(n + 1), 2))
    if cut1 == cut2:
        cut2 = min(n, cut1 + 1)

    child_a = _ox_offspring(parent_a, parent_b, cut1, cut2)
    child_b = _ox_offspring(parent_b, parent_a, cut1, cut2)
    return child_a, child_b


def _ox_offspring(
    primary: Sequence[int], secondary: Sequence[int], cut1: int, cut2: int
) -> list[int]:
    n = len(primary)
    child: list[int | None] = [None] * n
    segment = list(primary[cut1:cut2])
    for idx, gene in enumerate(segment):
        child[cut1 + idx] = gene
    fixed = set(segment)
    fill_iter = (gene for gene in (list(secondary[cut2:]) + list(secondary[:cut2])) if gene not in fixed)
    for idx in range(n):
        target = (cut2 + idx) % n
        if child[target] is None:
            try:
                child[target] = next(fill_iter)
            except StopIteration as exc:  # pragma: no cover - guarded by permutation invariant.
                raise RuntimeError("OX crossover ran out of fill genes") from exc
    return [gene for gene in child if gene is not None]
