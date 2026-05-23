"""Neighborhood moves for local search.

Every move accepts a :class:`Solution` and a :class:`random.Random` and
returns either a new :class:`Solution` (the candidate neighbour) or
``None`` if the operator could not produce a meaningful move on the
current state (e.g. ``two_opt`` on a route of length less than 4).

The candidate neighbour is always **feasible** because each move repairs
the affected routes via the central repair pipeline. This keeps the
acceptance logic in the SA simple: the algorithm only needs to compare
energies.

The five operators below form the "rich neighbourhood" recommended in the
VRP literature. Each one specialises in a different structural change:

================  ====================================================
Move              What it changes
================  ====================================================
``swap``          Exchange two customers (intra- or inter-route)
``relocate``      Take one customer out and re-insert it elsewhere
``or_opt``        Same as relocate but for a chain of 2-3 customers
``two_opt``       Reverse a sub-segment of one route (intra-route)
``two_opt_star``  Exchange the tails of two routes (inter-route)
================  ====================================================
"""

from __future__ import annotations

import random
from typing import Callable

from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.repair import repair_solution
from metaheuristics.core.solution import Route, Solution

NeighborhoodMove = Callable[[Solution, ProblemInstance, random.Random], Solution | None]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route_positions(solution: Solution) -> list[tuple[int, int]]:
    """Return ``[(route_index, position_in_route)]`` for every customer."""
    return [
        (route_idx, pos)
        for route_idx, route in enumerate(solution.routes)
        for pos in range(len(route.customers))
    ]


def _ensure_feasible(solution: Solution, instance: ProblemInstance) -> Solution:
    """Drop empty routes then run the repair pipeline."""
    solution.drop_empty_routes()
    return repair_solution(solution, instance)


# ---------------------------------------------------------------------------
# Swap
# ---------------------------------------------------------------------------


def swap_move(
    solution: Solution, instance: ProblemInstance, rng: random.Random
) -> Solution | None:
    """Swap two random customers (possibly in different routes)."""
    positions = _route_positions(solution)
    if len(positions) < 2:
        return None
    (r1, p1), (r2, p2) = rng.sample(positions, 2)
    neighbour = solution.clone()
    a = neighbour.routes[r1].customers[p1]
    b = neighbour.routes[r2].customers[p2]
    neighbour.routes[r1].customers[p1] = b
    neighbour.routes[r2].customers[p2] = a
    return _ensure_feasible(neighbour, instance)


# ---------------------------------------------------------------------------
# Relocate (or-opt-1)
# ---------------------------------------------------------------------------


def relocate_move(
    solution: Solution, instance: ProblemInstance, rng: random.Random
) -> Solution | None:
    """Remove one customer and reinsert it at a different position."""
    positions = _route_positions(solution)
    if not positions:
        return None
    source_route, source_pos = rng.choice(positions)
    neighbour = solution.clone()
    customer = neighbour.routes[source_route].customers.pop(source_pos)
    neighbour.drop_empty_routes()

    if not neighbour.routes:
        neighbour.routes.append(Route([customer]))
        return _ensure_feasible(neighbour, instance)

    insertion_points: list[tuple[int, int]] = [
        (route_idx, pos)
        for route_idx, route in enumerate(neighbour.routes)
        for pos in range(len(route.customers) + 1)
    ]
    insertion_points.append((len(neighbour.routes), 0))  # start a new route
    target_route, target_pos = rng.choice(insertion_points)
    if target_route == len(neighbour.routes):
        neighbour.routes.append(Route([customer]))
    else:
        neighbour.routes[target_route].customers.insert(target_pos, customer)
    return _ensure_feasible(neighbour, instance)


# ---------------------------------------------------------------------------
# Or-opt (chains of 2 or 3 consecutive customers)
# ---------------------------------------------------------------------------


def or_opt_move(
    solution: Solution, instance: ProblemInstance, rng: random.Random
) -> Solution | None:
    """Move a chain of 2 or 3 consecutive customers to a new position."""
    candidate_routes = [
        (idx, route)
        for idx, route in enumerate(solution.routes)
        if len(route.customers) >= 2
    ]
    if not candidate_routes:
        return None
    source_idx, source_route = rng.choice(candidate_routes)
    chain_length = rng.choice([n for n in (2, 3) if n <= len(source_route.customers)])
    start = rng.randint(0, len(source_route.customers) - chain_length)
    neighbour = solution.clone()
    chain = neighbour.routes[source_idx].customers[start : start + chain_length]
    del neighbour.routes[source_idx].customers[start : start + chain_length]
    neighbour.drop_empty_routes()

    insertion_points: list[tuple[int, int]] = [
        (route_idx, pos)
        for route_idx, route in enumerate(neighbour.routes)
        for pos in range(len(route.customers) + 1)
    ]
    insertion_points.append((len(neighbour.routes), 0))
    target_route, target_pos = rng.choice(insertion_points)
    if target_route == len(neighbour.routes):
        neighbour.routes.append(Route(list(chain)))
    else:
        neighbour.routes[target_route].customers[target_pos:target_pos] = chain
    return _ensure_feasible(neighbour, instance)


# ---------------------------------------------------------------------------
# 2-opt (intra-route segment reversal)
# ---------------------------------------------------------------------------


def two_opt_move(
    solution: Solution, instance: ProblemInstance, rng: random.Random
) -> Solution | None:
    """Reverse a sub-segment of one route to undo crossings.

    Note that with an asymmetric cost matrix the reversed segment may have
    a different cost in either direction; the repair/evaluation downstream
    decides whether the move is worth keeping.
    """
    candidates = [idx for idx, route in enumerate(solution.routes) if len(route.customers) >= 4]
    if not candidates:
        return None
    route_idx = rng.choice(candidates)
    customers = solution.routes[route_idx].customers
    i = rng.randint(0, len(customers) - 2)
    j = rng.randint(i + 1, len(customers) - 1)
    if (j - i) < 2:
        return None
    neighbour = solution.clone()
    target = neighbour.routes[route_idx].customers
    target[i : j + 1] = list(reversed(target[i : j + 1]))
    return _ensure_feasible(neighbour, instance)


# ---------------------------------------------------------------------------
# 2-opt* (inter-route tail exchange)
# ---------------------------------------------------------------------------


def two_opt_star_move(
    solution: Solution, instance: ProblemInstance, rng: random.Random
) -> Solution | None:
    """Exchange the tails of two distinct routes.

    Given two routes ``A = [a_1, ..., a_k]`` and ``B = [b_1, ..., b_m]``,
    pick split points ``i`` and ``j``, then produce::

        A' = a_1..a_i + b_{j+1}..b_m
        B' = b_1..b_j + a_{i+1}..a_k

    This is the canonical inter-route move that lets the local search
    balance load and travel distance between drones.
    """
    if len(solution.routes) < 2:
        return None
    a_idx, b_idx = rng.sample(range(len(solution.routes)), 2)
    a_customers = solution.routes[a_idx].customers
    b_customers = solution.routes[b_idx].customers
    if not a_customers or not b_customers:
        return None
    i = rng.randint(0, len(a_customers))
    j = rng.randint(0, len(b_customers))
    new_a = a_customers[:i] + b_customers[j:]
    new_b = b_customers[:j] + a_customers[i:]
    neighbour = solution.clone()
    neighbour.routes[a_idx].customers = new_a
    neighbour.routes[b_idx].customers = new_b
    return _ensure_feasible(neighbour, instance)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


NEIGHBORHOOD_MOVES: tuple[NeighborhoodMove, ...] = (
    swap_move,
    relocate_move,
    or_opt_move,
    two_opt_move,
    two_opt_star_move,
)
