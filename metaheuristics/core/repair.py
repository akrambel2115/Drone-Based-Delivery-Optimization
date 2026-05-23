"""Feasibility-restoring repair operators.

A neighbourhood move or a mutation can produce an infeasible route — most
commonly a route that overshoots the **battery budget** after a customer is
inserted, or whose **payload** exceeds the drone capacity. The repair
operators here transform such a partition into a feasible one by inserting
return-to-depot stops at the best possible position.

The strategy is the one suggested by the project statement: when a drone
exceeds its battery limit, split the route and "swap the battery" by
returning to the depot. The same primitive handles payload overflow.

The implementation is deliberately greedy and deterministic:

1. Walk the customers in their current order.
2. Maintain a prefix that is still feasible (payload + battery).
3. As soon as adding the next customer would violate a constraint, close
   the current route at the previous customer and start a new one.

This keeps the order of customers stable, which preserves crossover /
neighborhood semantics. A reordering pass (2-opt / or-opt) is a separate
concern and is delegated to the neighborhood module.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from metaheuristics.core.evaluator import evaluate_route, route_demand
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Route, Solution

_FEASIBILITY_TOLERANCE = 1e-6


def split_overlong_route(
    customers: Sequence[int], instance: ProblemInstance
) -> list[list[int]]:
    """Split a single (possibly infeasible) customer sequence into feasible chunks.

    The split respects payload capacity *and* battery capacity while preserving
    the original customer order.

    Raises
    ------
    ValueError
        If a single customer cannot be served by one drone (its demand exceeds
        ``payload_capacity`` or the depot round-trip already exceeds
        ``battery_capacity``). The data generator guarantees this never
        happens for benchmark instances, so this error effectively only
        catches programming bugs.
    """
    drone = instance.drone
    chunks: list[list[int]] = []
    current: list[int] = []
    current_load = 0

    for customer in customers:
        demand = instance.demand_by_id[customer]
        round_trip = instance.cost(0, customer) + instance.cost(customer, 0)
        if demand > drone.payload_capacity:
            raise ValueError(
                f"Customer {customer} has demand {demand} > payload {drone.payload_capacity}"
            )
        if round_trip > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
            raise ValueError(
                f"Customer {customer} requires {round_trip:.4f} energy > "
                f"battery {drone.battery_capacity}"
            )

        candidate = current + [customer]
        candidate_load = current_load + demand
        candidate_energy = evaluate_route(candidate, instance)

        if (
            candidate_load <= drone.payload_capacity
            and candidate_energy <= drone.battery_capacity + _FEASIBILITY_TOLERANCE
        ):
            current = candidate
            current_load = candidate_load
        else:
            if current:
                chunks.append(current)
            current = [customer]
            current_load = demand

    if current:
        chunks.append(current)
    return chunks


def repair_solution(solution: Solution, instance: ProblemInstance) -> Solution:
    """Return a new feasible solution preserving customer order per route.

    The repair pipeline:

    1. Drop empty routes.
    2. Split each route that violates payload or battery into feasible chunks.
    3. If the resulting solution exceeds the fleet-size limit, merge tail
       routes greedily as long as feasibility allows. Routes that cannot be
       merged are kept (the result may still be fleet-infeasible — the caller
       must reflect that as a penalty in the fitness).
    """
    repaired = Solution()
    for route in solution.routes:
        if not route.customers:
            continue
        chunks = split_overlong_route(route.customers, instance)
        repaired.routes.extend(Route(chunk) for chunk in chunks)

    if instance.drone.fleet_limited:
        _merge_until_fleet_fits(repaired, instance)

    return repaired


def _merge_until_fleet_fits(solution: Solution, instance: ProblemInstance) -> None:
    """Greedy fleet-fitting: try to merge route pairs whose combined trip is feasible."""
    drone = instance.drone
    target = drone.fleet_size
    if target is None:
        return
    while solution.num_routes > target:
        merged = _try_merge_one(solution, instance)
        if not merged:
            return  # Cannot satisfy the fleet bound by merging; caller will penalise.


def _try_merge_one(solution: Solution, instance: ProblemInstance) -> bool:
    drone = instance.drone
    for i in range(len(solution.routes)):
        for j in range(len(solution.routes)):
            if i == j:
                continue
            combined = solution.routes[i].customers + solution.routes[j].customers
            load = route_demand(combined, instance)
            if load > drone.payload_capacity:
                continue
            if evaluate_route(combined, instance) > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
                continue
            solution.routes[i].customers = combined
            del solution.routes[j]
            return True
    return False
