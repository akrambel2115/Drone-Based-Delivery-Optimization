"""Energy and feasibility computation.

All functions in this module are **pure**: they never mutate their inputs
and never read global state. They operate on the canonical asymmetric
cost matrix exposed by :class:`ProblemInstance` so that the metaheuristics
share the exact same cost model as the data generator and the exact method.

A route ``r = [c_1, ..., c_k]`` has energy::

    cost[0][c_1] + sum(cost[c_i][c_{i+1}]) + cost[c_k][0]

(``0`` is the depot). An empty route has zero energy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Solution

_FEASIBILITY_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Evaluation:
    """Outcome of evaluating a candidate :class:`Solution`.

    ``energy`` is the objective value (total energy spent across drones).
    When ``feasible`` is ``False`` the energy still reflects the actual route
    costs, but at least one constraint is violated; ``violations`` lists the
    machine-readable reasons.
    """

    energy: float
    feasible: bool
    num_routes: int
    violations: tuple[str, ...] = ()

    @property
    def penalised_energy(self) -> float:
        """Helper for metaheuristics that mix feasibility into the fitness."""
        return self.energy


def evaluate_route(route_customers: Sequence[int], instance: ProblemInstance) -> float:
    """Return the energy of a closed route starting and ending at the depot."""
    if not route_customers:
        return 0.0
    cost = instance.cost
    total = cost(0, route_customers[0])
    for left, right in zip(route_customers, route_customers[1:]):
        total += cost(left, right)
    total += cost(route_customers[-1], 0)
    return total


def total_energy(solution: Solution, instance: ProblemInstance) -> float:
    return sum(evaluate_route(route.customers, instance) for route in solution.routes)


def route_demand(route_customers: Iterable[int], instance: ProblemInstance) -> int:
    demand_by_id = instance.demand_by_id
    return sum(demand_by_id[c] for c in route_customers)


def is_feasible(solution: Solution, instance: ProblemInstance) -> bool:
    """Quick boolean feasibility check that short-circuits on the first issue."""
    drone = instance.drone
    visited: set[int] = set()
    for route in solution.routes:
        load = 0
        for customer in route.customers:
            load += instance.demand_by_id[customer]
            if customer in visited:
                return False
            visited.add(customer)
        if load > drone.payload_capacity:
            return False
        if evaluate_route(route.customers, instance) > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
            return False
    if drone.fleet_limited and solution.num_routes > (drone.fleet_size or 0):
        return False
    return visited == set(instance.customer_ids)


def evaluate_solution(solution: Solution, instance: ProblemInstance) -> Evaluation:
    """Full evaluation that gathers the energy *and* every constraint violation."""
    drone = instance.drone
    violations: list[str] = []
    energy = 0.0
    visited: list[int] = []

    for route_idx, route in enumerate(solution.routes, start=1):
        if not route.customers:
            continue
        load = sum(instance.demand_by_id[c] for c in route.customers)
        route_energy = evaluate_route(route.customers, instance)
        energy += route_energy
        visited.extend(route.customers)
        if load > drone.payload_capacity:
            violations.append(
                f"route {route_idx} payload {load} > {drone.payload_capacity}"
            )
        if route_energy > drone.battery_capacity + _FEASIBILITY_TOLERANCE:
            violations.append(
                f"route {route_idx} energy {route_energy:.4f} > "
                f"battery {drone.battery_capacity}"
            )

    if drone.fleet_limited and solution.num_routes > (drone.fleet_size or 0):
        violations.append(
            f"fleet usage {solution.num_routes} > limit {drone.fleet_size}"
        )

    expected = set(instance.customer_ids)
    visited_set = set(visited)
    if len(visited) != len(visited_set):
        violations.append("duplicate customer visits")
    missing = expected - visited_set
    if missing:
        violations.append(f"missing customers: {sorted(missing)}")
    extra = visited_set - expected
    if extra:
        violations.append(f"unknown customer IDs: {sorted(extra)}")

    return Evaluation(
        energy=energy,
        feasible=not violations,
        num_routes=sum(1 for r in solution.routes if r.customers),
        violations=tuple(violations),
    )
