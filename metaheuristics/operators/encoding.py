"""Encoding operators: list-of-routes <-> giant-tour permutation.

The GA evolves a **giant tour**: a permutation of the ``N`` customer IDs.
A giant tour ``s = (s_1, ..., s_N)`` is decoded to a list of routes by an
optimal *Split* procedure (Prins, 2004) that, given the order ``s``, returns
the partition into feasible routes with minimum total energy.

Split is the key idea that makes the GA effective for VRP-style problems:

* Crossover and mutation work on simple permutations (no explicit depot
  bookkeeping, no infeasible offspring from misplaced depot markers).
* Decoding folds capacity and battery constraints into a clean DP, so
  every chromosome corresponds to a feasible solution (provided that a
  feasible partition exists for the given sequence, which holds whenever
  each customer fits a single round-trip from the depot).

Complexity
----------
* :func:`split_giant_tour` runs in ``O(N^2)`` time (one pass per starting
  position, with an early break once payload or battery overflow).
* :func:`giant_tour_from_solution` is linear.

Reference
---------
Prins, C. (2004). *A simple and effective evolutionary algorithm for the
vehicle routing problem*. Computers & Operations Research 31(12), 1985–2002.
"""

from __future__ import annotations

import math
from typing import Sequence

from metaheuristics.core.evaluator import evaluate_route
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Route, Solution

_FEASIBILITY_TOLERANCE = 1e-6


def giant_tour_from_solution(solution: Solution) -> list[int]:
    """Drop depot markers and return the concatenated customer order."""
    return solution.all_customers()


def solution_from_giant_tour(
    tour: Sequence[int], instance: ProblemInstance
) -> Solution:
    """Convenience wrapper around :func:`split_giant_tour`."""
    return split_giant_tour(tour, instance)


def split_giant_tour(tour: Sequence[int], instance: ProblemInstance) -> Solution:
    """Optimal partition of a giant tour into feasible drone routes.

    Implements Prins' (2004) ``Split`` procedure for the asymmetric cost
    matrix used in this project. The DP keeps an incremental route cost so
    that each transition is ``O(1)``.

    Notes
    -----
    The DP enforces payload and battery constraints. The fleet-size
    constraint is **not** modelled here; if the optimal split uses more
    routes than the drone fleet allows, the surplus is reported as an
    extra route and the caller is expected to penalise it in the fitness.
    Solving the fleet-bounded variant exactly would require an extra
    ``O(N * K)`` dimension in the DP — not worthwhile at the sizes used in
    this study.
    """
    n = len(tour)
    if n == 0:
        return Solution()

    drone = instance.drone
    cost = instance.cost
    demand = instance.demand_by_id

    # Validate that every single-customer trip is feasible. The data
    # generator guarantees this; the check is cheap insurance.
    for customer in tour:
        if demand[customer] > drone.payload_capacity:
            raise ValueError(f"Customer {customer} demand exceeds payload capacity")
        if cost(0, customer) + cost(customer, 0) > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
            raise ValueError(f"Customer {customer} cannot be served within battery budget")

    V = [math.inf] * (n + 1)
    P = [0] * (n + 1)
    V[0] = 0.0

    for j in range(n):
        if math.isinf(V[j]):
            continue
        load = 0
        inner_cost = 0.0  # accumulated cost depot -> ... -> tour[i] (without final leg back)
        for i in range(j, n):
            customer = tour[i]
            load += demand[customer]
            if load > drone.payload_capacity:
                break
            if i == j:
                inner_cost = cost(0, customer)
            else:
                inner_cost += cost(tour[i - 1], customer)
            route_cost = inner_cost + cost(customer, 0)
            if route_cost > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
                break
            candidate = V[j] + route_cost
            if candidate < V[i + 1]:
                V[i + 1] = candidate
                P[i + 1] = j

    if math.isinf(V[n]):  # pragma: no cover - guarded by the per-customer check above.
        raise ValueError("No feasible split exists for the given giant tour")

    # Reconstruct routes by walking the predecessor chain back to 0.
    boundaries: list[int] = []
    cursor = n
    while cursor > 0:
        boundaries.append(cursor)
        cursor = P[cursor]
    boundaries.append(0)
    boundaries.reverse()

    routes: list[Route] = []
    for start, end in zip(boundaries, boundaries[1:]):
        routes.append(Route(list(tour[start:end])))
    return Solution(routes=routes)


def solution_total_energy_from_tour(tour: Sequence[int], instance: ProblemInstance) -> float:
    """Cheap helper: split a tour and return its total energy without keeping the structure."""
    solution = split_giant_tour(tour, instance)
    return sum(evaluate_route(route.customers, instance) for route in solution.routes)
