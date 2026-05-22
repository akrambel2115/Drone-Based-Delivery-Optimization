"""Constructive baseline route certificate."""

from __future__ import annotations

from dataclasses import dataclass

from data_generator.errors import PlacementError
from data_generator.models import BaselineRoute, Customer, DroneProfile, InstanceSpec


@dataclass
class _WorkingRoute:
    customer_ids: list[int]
    total_demand: int


def build_baseline_routes(
    customers: list[Customer],
    travel_cost_matrix: list[list[float]],
    node_ids: list[int],
    profile: DroneProfile,
    spec: InstanceSpec,
) -> list[BaselineRoute]:
    id_to_customer = {customer.id: customer for customer in customers}
    id_to_index = {node_id: idx for idx, node_id in enumerate(node_ids)}
    sorted_customers = sorted(
        customers,
        key=lambda c: (
            -c.demand,
            -(travel_cost_matrix[0][id_to_index[c.id]] + travel_cost_matrix[id_to_index[c.id]][0]),
            c.id,
        ),
    )

    routes: list[_WorkingRoute] = []
    for customer in sorted_customers:
        best: tuple[float, int, int] | None = None
        for route_idx, route in enumerate(routes):
            if route.total_demand + customer.demand > profile.payload_capacity:
                continue
            for insert_at in range(len(route.customer_ids) + 1):
                candidate_ids = (
                    route.customer_ids[:insert_at]
                    + [customer.id]
                    + route.customer_ids[insert_at:]
                )
                energy = route_energy(candidate_ids, travel_cost_matrix, id_to_index)
                if energy <= profile.battery_capacity:
                    current = route_energy(route.customer_ids, travel_cost_matrix, id_to_index)
                    increase = energy - current
                    if best is None or increase < best[0]:
                        best = (increase, route_idx, insert_at)
        if best is not None:
            _, route_idx, insert_at = best
            route = routes[route_idx]
            route.customer_ids.insert(insert_at, customer.id)
            route.total_demand += customer.demand
            continue

        singleton_energy = route_energy([customer.id], travel_cost_matrix, id_to_index)
        if customer.demand > profile.payload_capacity:
            raise PlacementError(f"Customer {customer.id} exceeds payload capacity")
        if singleton_energy > profile.battery_capacity:
            raise PlacementError(f"Customer {customer.id} exceeds battery capacity")
        if (
            spec.feature_flags.fleet_size_limited
            and profile.fleet_size is not None
            and len(routes) + 1 > profile.fleet_size
        ):
            raise PlacementError("Baseline route construction exceeded fleet size")
        routes.append(_WorkingRoute([customer.id], customer.demand))

    finalized: list[BaselineRoute] = []
    for route_id, route in enumerate(routes, start=1):
        improved_ids = two_opt(route.customer_ids, travel_cost_matrix, id_to_index)
        demand = sum(id_to_customer[cid].demand for cid in improved_ids)
        energy = route_energy(improved_ids, travel_cost_matrix, id_to_index)
        if demand > profile.payload_capacity or energy > profile.battery_capacity:
            raise PlacementError(f"Route {route_id} is infeasible after optimization")
        finalized.append(
            BaselineRoute(
                route_id=route_id,
                customers=improved_ids,
                total_demand=demand,
                total_energy=round(energy, 4),
            )
        )

    if (
        spec.feature_flags.fleet_size_limited
        and profile.fleet_size is not None
        and len(finalized) > profile.fleet_size
    ):
        raise PlacementError("Baseline certificate exceeds fleet size")
    return finalized


def route_energy(
    customer_ids: list[int],
    travel_cost_matrix: list[list[float]],
    id_to_index: dict[int, int],
) -> float:
    if not customer_ids:
        return 0.0
    total = travel_cost_matrix[0][id_to_index[customer_ids[0]]]
    for left, right in zip(customer_ids, customer_ids[1:]):
        total += travel_cost_matrix[id_to_index[left]][id_to_index[right]]
    total += travel_cost_matrix[id_to_index[customer_ids[-1]]][0]
    return round(total, 4)


def two_opt(
    customer_ids: list[int],
    travel_cost_matrix: list[list[float]],
    id_to_index: dict[int, int],
) -> list[int]:
    best = list(customer_ids)
    if len(best) < 4:
        return best
    improved = True
    while improved:
        improved = False
        current_energy = route_energy(best, travel_cost_matrix, id_to_index)
        for i in range(len(best) - 1):
            for j in range(i + 2, len(best) + 1):
                candidate = best[:i] + list(reversed(best[i:j])) + best[j:]
                candidate_energy = route_energy(candidate, travel_cost_matrix, id_to_index)
                if candidate_energy + 1e-9 < current_energy:
                    best = candidate
                    improved = True
                    break
            if improved:
                break
    return best
