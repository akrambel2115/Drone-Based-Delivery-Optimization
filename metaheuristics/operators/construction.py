"""Construction operators: building an initial feasible solution.

Two complementary heuristics are provided:

* :func:`nearest_neighbor` — classical greedy that extends the current
  route to the nearest still-feasible customer. Cheap and order-driven, it
  gives the SA a reasonable warm start in O(N^2) time.
* :func:`clarke_wright_savings` — the Clarke-Wright savings algorithm
  adapted for the asymmetric cost matrix. It tends to produce structurally
  better solutions than nearest-neighbour and is used to seed the GA
  population alongside random tours.

Both operators always return a **feasible** solution with respect to
payload and battery; if the optional fleet-size limit cannot be met, the
caller is expected to repair or penalise the result.
"""

from __future__ import annotations

import random
from typing import Iterable

from metaheuristics.core.evaluator import evaluate_route
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Route, Solution
from metaheuristics.operators.encoding import split_giant_tour

_FEASIBILITY_TOLERANCE = 1e-6


def nearest_neighbor(instance: ProblemInstance, rng: random.Random | None = None) -> Solution:
    """Greedy nearest-neighbour construction.

    Starts a new route from the depot, repeatedly extends it with the
    closest unvisited customer that keeps both payload and battery feasible.
    When no candidate fits, the drone returns to the depot and a new route
    is started.

    The optional ``rng`` is used to break ties deterministically when
    multiple customers share the same cost.
    """
    drone = instance.drone
    cost = instance.cost
    demand = instance.demand_by_id
    remaining = set(instance.customer_ids)
    routes: list[Route] = []

    while remaining:
        current_customers: list[int] = []
        current_load = 0
        current_position = 0  # depot

        while True:
            best_customer = _best_extension(
                remaining,
                current_customers,
                current_load,
                current_position,
                drone,
                cost,
                demand,
                rng,
            )
            if best_customer is None:
                break
            current_customers.append(best_customer)
            current_load += demand[best_customer]
            current_position = best_customer
            remaining.discard(best_customer)

        if not current_customers:
            # No customer fits even an empty drone — protected by the per-customer
            # feasibility guarantee of the data generator. Defensive only.
            raise RuntimeError("Nearest-neighbour stuck with no feasible extension")
        routes.append(Route(current_customers))

    return Solution(routes=routes)


def _best_extension(
    remaining: Iterable[int],
    current_customers: list[int],
    current_load: int,
    current_position: int,
    drone,
    cost,
    demand,
    rng: random.Random | None,
) -> int | None:
    best: tuple[float, int] | None = None
    for candidate in remaining:
        new_load = current_load + demand[candidate]
        if new_load > drone.payload_capacity:
            continue
        extended = current_customers + [candidate]
        if evaluate_route_inline(extended, cost) > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
            continue
        edge_cost = cost(current_position, candidate)
        if best is None or edge_cost < best[0]:
            best = (edge_cost, candidate)
        elif edge_cost == best[0] and rng is not None and rng.random() < 0.5:
            best = (edge_cost, candidate)
    if best is None:
        return None
    return best[1]


def evaluate_route_inline(customers: list[int], cost) -> float:
    """Mirror of :func:`metaheuristics.core.evaluator.evaluate_route` for closures."""
    if not customers:
        return 0.0
    total = cost(0, customers[0])
    for left, right in zip(customers, customers[1:]):
        total += cost(left, right)
    total += cost(customers[-1], 0)
    return total


def clarke_wright_savings(instance: ProblemInstance) -> Solution:
    """Clarke-Wright savings construction (asymmetric variant).

    For every pair ``(i, j)`` of customers, the savings of merging the
    singleton routes ``[i]`` and ``[j]`` into ``[i, j]`` is::

        s(i, j) = cost(i, 0) + cost(0, j) - cost(i, j)

    The algorithm starts with one route per customer and iteratively merges
    the pair with the largest positive savings as long as the merged route
    stays feasible. The asymmetric cost is handled by considering both
    orderings ``(i, j)`` and ``(j, i)``.
    """
    drone = instance.drone
    cost = instance.cost
    demand = instance.demand_by_id

    routes: dict[int, list[int]] = {c: [c] for c in instance.customer_ids}
    route_load: dict[int, int] = {c: demand[c] for c in instance.customer_ids}

    pairs: list[tuple[float, int, int]] = []
    customer_ids = list(instance.customer_ids)
    for i in customer_ids:
        for j in customer_ids:
            if i == j:
                continue
            savings = cost(i, 0) + cost(0, j) - cost(i, j)
            pairs.append((savings, i, j))
    pairs.sort(key=lambda triple: -triple[0])

    head_of: dict[int, int] = {c: c for c in customer_ids}  # route head ID
    tail_of: dict[int, int] = {c: c for c in customer_ids}

    for savings, i, j in pairs:
        if savings <= 0:
            break
        route_i = head_of.get(i)
        route_j = head_of.get(j)
        if route_i is None or route_j is None or route_i == route_j:
            continue
        # Only allow merging if i is the tail of its route and j is the head of its route
        if routes[route_i][-1] != i or routes[route_j][0] != j:
            continue
        new_load = route_load[route_i] + route_load[route_j]
        if new_load > drone.payload_capacity:
            continue
        merged = routes[route_i] + routes[route_j]
        if evaluate_route(merged, instance) > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
            continue

        # Commit the merge under route_i; route_j disappears.
        routes[route_i] = merged
        route_load[route_i] = new_load
        for node in routes[route_j]:
            head_of[node] = route_i
            tail_of[node] = route_i
        del routes[route_j]

    solution = Solution(routes=[Route(list(seq)) for seq in routes.values()])
    return solution


def random_split(instance: ProblemInstance, rng: random.Random) -> Solution:
    """Random giant tour decoded by Prins' optimal Split."""
    customers = list(instance.customer_ids)
    rng.shuffle(customers)
    return split_giant_tour(customers, instance)
