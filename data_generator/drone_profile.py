"""Drone capacity auto-sizing."""

from __future__ import annotations

import math

from data_generator.models import Customer, Depot, DroneProfile, InstanceSpec, TravelMatrices


def compute_profile(
    spec: InstanceSpec,
    depot: Depot,
    customers: list[Customer],
    travel_matrices: TravelMatrices,
) -> DroneProfile:
    _ = depot
    total_demand = sum(customer.demand for customer in customers)
    max_demand = max(customer.demand for customer in customers)

    if spec.feature_flags.fleet_size_limited and spec.drone_profile.fleet_size:
        target_route_count = spec.drone_profile.fleet_size
    else:
        target_route_count = max(
            1,
            math.ceil(len(customers) / spec.drone_profile.target_customers_per_route),
        )

    if spec.drone_profile.auto_size_payload:
        target_max = max(0.01, spec.drone_profile.target_payload_utilization_max)
        payload_capacity = max(
            spec.drone_profile.payload_capacity,
            max_demand,
            math.ceil(total_demand / max(1, target_route_count * target_max)),
        )
    else:
        payload_capacity = spec.drone_profile.payload_capacity

    if spec.feature_flags.fleet_size_limited:
        fleet_size = spec.drone_profile.fleet_size
        if fleet_size is None:
            fleet_size = math.ceil(total_demand / payload_capacity) + spec.drone_profile.fleet_slack
    else:
        fleet_size = None

    if spec.drone_profile.auto_size_battery:
        worst_round_trip = _worst_single_customer_round_trip(travel_matrices)
        battery_capacity = max(
            spec.drone_profile.battery_capacity,
            worst_round_trip * spec.drone_profile.battery_slack,
        )
        if fleet_size is not None:
            max_pair_cost = max(max(row) for row in travel_matrices.costs)
            customers_per_route = math.ceil(len(customers) / max(1, fleet_size))
            conservative_route_edges = customers_per_route + 1
            battery_capacity = max(
                battery_capacity,
                max_pair_cost * conservative_route_edges * 1.10,
            )
    else:
        battery_capacity = spec.drone_profile.battery_capacity

    return DroneProfile(
        payload_capacity=int(payload_capacity),
        battery_capacity=round(float(battery_capacity), 4),
        fleet_size=fleet_size,
    )


def _worst_single_customer_round_trip(travel_matrices: TravelMatrices) -> float:
    worst = 0.0
    for idx in range(1, len(travel_matrices.node_ids)):
        worst = max(worst, travel_matrices.costs[0][idx] + travel_matrices.costs[idx][0])
    return worst
