"""Customer placement."""

from __future__ import annotations

import random

import numpy as np

from data_generator.errors import PlacementError
from data_generator.models import Customer, Depot, InstanceSpec


def place_customers(
    spec: InstanceSpec,
    depot: Depot,
    height_map: np.ndarray | None,
    rng: random.Random,
) -> list[Customer]:
    customers: list[Customer] = []
    for customer_id in range(1, spec.customers.count + 1):
        accepted = None
        for _ in range(spec.customers.max_placement_retries):
            x = rng.randrange(spec.grid.x_size)
            y = rng.randrange(spec.grid.y_size)
            if x == depot.x and y == depot.y:
                continue
            if _too_close(x, y, customers, spec.customers.min_separation):
                continue
            z = int(height_map[x, y]) if height_map is not None else 0
            if not (0 <= z < spec.grid.z_size):
                continue
            demand = rng.randint(spec.customers.demand_min, spec.customers.demand_max)
            if (
                not spec.drone_profile.auto_size_payload
                and demand > spec.drone_profile.payload_capacity
            ):
                continue
            accepted = Customer(id=customer_id, x=x, y=y, z=z, demand=demand)
            break
        if accepted is None:
            raise PlacementError(f"Could not place customer {customer_id}")
        customers.append(accepted)
    return customers


def _too_close(x: int, y: int, customers: list[Customer], min_separation: int) -> bool:
    for customer in customers:
        if max(abs(x - customer.x), abs(y - customer.y)) < min_separation:
            return True
    return False
