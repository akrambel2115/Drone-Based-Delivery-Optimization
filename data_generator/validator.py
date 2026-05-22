"""Instance validation."""

from __future__ import annotations

import math
from typing import Any

from data_generator.models import InstanceSpec, ValidationReport
from data_generator.nfz import boxes_overlap, point_inside_box
from data_generator.route_feasibility import route_energy


def validate_instance(spec: InstanceSpec, instance: dict[str, Any]) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    required_top_level = [
        "metadata",
        "drone_profile",
        "energy_costs",
        "pathfinding",
        "travel_matrix_node_ids",
        "travel_cost_matrix",
        "travel_distance_matrix",
        "terrain",
        "depot",
        "customers",
        "no_fly_zones",
        "collision",
        "baseline_feasible_routes",
    ]
    for key in required_top_level:
        if key not in instance:
            errors.append(f"Missing top-level key: {key}")
    if errors:
        return ValidationReport(False, errors, warnings)

    metadata = instance["metadata"]
    depot = instance["depot"]
    customers = instance["customers"]
    nfzs = instance["no_fly_zones"]
    profile = instance["drone_profile"]
    terrain = instance["terrain"]
    node_ids = instance["travel_matrix_node_ids"]
    cost_matrix = instance["travel_cost_matrix"]
    distance_matrix = instance["travel_distance_matrix"]
    baseline_routes = instance["baseline_feasible_routes"]

    if metadata.get("instance_name") != spec.instance_name:
        errors.append("metadata.instance_name does not match spec")
    if metadata.get("scenario_type") != spec.scenario_type:
        errors.append("metadata.scenario_type does not match spec")
    if metadata.get("random_seed") != spec.generation.random_seed:
        errors.append("metadata.random_seed does not match spec")
    if metadata.get("schema_version") != spec.schema_version:
        errors.append("metadata.schema_version does not match spec")

    _validate_entity_bounds("depot", depot, spec, errors)
    customer_ids: list[int] = []
    for customer in customers:
        _validate_entity_bounds(f"customer {customer.get('id')}", customer, spec, errors)
        customer_ids.append(customer.get("id"))
        if customer.get("demand", 0) > profile["payload_capacity"]:
            errors.append(f"Customer {customer.get('id')} exceeds payload capacity")
    if len(customer_ids) != len(set(customer_ids)):
        errors.append("Customer IDs are not unique")
    if depot.get("id") != 0:
        errors.append("Depot ID must be 0")
    if sorted(customer_ids) != list(range(1, len(customers) + 1)):
        errors.append("Customer IDs must be contiguous from 1")

    if spec.feature_flags.terrain_enabled:
        if not terrain.get("enabled"):
            errors.append("Terrain flag is enabled but terrain section is disabled")
        height_map = terrain.get("height_map")
        if not isinstance(height_map, list):
            errors.append("Terrain height_map must be present when terrain is enabled")
        else:
            _validate_height_match("depot", depot, height_map, errors)
            for customer in customers:
                _validate_height_match(f"customer {customer['id']}", customer, height_map, errors)
    else:
        if terrain.get("enabled"):
            errors.append("Terrain section enabled while terrain flag is off")
        if terrain.get("height_map") is not None:
            errors.append("Terrain height_map must be null when disabled")
        if depot.get("z") != 0:
            errors.append("Depot z must be 0 when terrain is disabled")
        for customer in customers:
            if customer.get("z") != 0:
                errors.append(f"Customer {customer.get('id')} z must be 0 when terrain is disabled")

    for box in nfzs:
        if not _box_in_bounds(box, spec):
            errors.append(f"NFZ {box.get('id')} is out of bounds")
        if point_inside_box(depot["x"], depot["y"], depot["z"], _box_obj(box)):
            errors.append(f"Depot lies inside NFZ {box.get('id')}")
        for customer in customers:
            if point_inside_box(customer["x"], customer["y"], customer["z"], _box_obj(box)):
                errors.append(f"Customer {customer['id']} lies inside NFZ {box.get('id')}")
    for idx, left in enumerate(nfzs):
        for right in nfzs[idx + 1 :]:
            if boxes_overlap(_box_obj(left), _box_obj(right)):
                errors.append(f"NFZ {left.get('id')} overlaps NFZ {right.get('id')}")

    expected_node_ids = [0] + customer_ids
    if node_ids != expected_node_ids:
        errors.append("travel_matrix_node_ids must be [0, customer_1.id, ...]")
    _validate_matrix("travel_cost_matrix", cost_matrix, len(expected_node_ids), errors)
    _validate_matrix("travel_distance_matrix", distance_matrix, len(expected_node_ids), errors)
    if not errors:
        for idx, customer in enumerate(customers, start=1):
            round_trip = cost_matrix[0][idx] + cost_matrix[idx][0]
            if round_trip > profile["battery_capacity"] + 1e-6:
                errors.append(f"Customer {customer['id']} exceeds single-customer battery")
        symmetric_energy = math.isclose(
            spec.energy_costs.vertical_ascend_multiplier,
            spec.energy_costs.vertical_descend_multiplier,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        if symmetric_energy:
            for i in range(len(expected_node_ids)):
                for j in range(len(expected_node_ids)):
                    if abs(cost_matrix[i][j] - cost_matrix[j][i]) > 1e-4:
                        errors.append("travel_cost_matrix must be symmetric under symmetric energy")
                        break

    id_to_customer = {customer["id"]: customer for customer in customers}
    id_to_index = {node_id: idx for idx, node_id in enumerate(node_ids)}
    served: list[int] = []
    for route in baseline_routes:
        route_customer_ids = route.get("customers", [])
        served.extend(route_customer_ids)
        demand = sum(id_to_customer[cid]["demand"] for cid in route_customer_ids if cid in id_to_customer)
        if demand != route.get("total_demand"):
            errors.append(f"Route {route.get('route_id')} demand total is incorrect")
        if demand > profile["payload_capacity"]:
            errors.append(f"Route {route.get('route_id')} exceeds payload capacity")
        if not errors:
            energy = route_energy(route_customer_ids, cost_matrix, id_to_index)
            if abs(energy - route.get("total_energy", -1)) > 1e-3:
                errors.append(f"Route {route.get('route_id')} energy total is incorrect")
            if energy > profile["battery_capacity"] + 1e-6:
                errors.append(f"Route {route.get('route_id')} exceeds battery capacity")
    if sorted(served) != expected_node_ids[1:]:
        errors.append("baseline_feasible_routes must serve every customer exactly once")

    fleet_size = profile.get("fleet_size")
    if spec.feature_flags.fleet_size_limited:
        if not isinstance(fleet_size, int) or fleet_size <= 0:
            errors.append("fleet_size must be a positive integer when fleet is limited")
        elif len(baseline_routes) > fleet_size:
            errors.append("baseline_feasible_routes exceeds fleet_size")
        total_demand = sum(customer["demand"] for customer in customers)
        if isinstance(fleet_size, int) and total_demand > fleet_size * profile["payload_capacity"]:
            errors.append("total demand exceeds fleet payload capacity")
    elif fleet_size is not None:
        errors.append("fleet_size must be null when fleet is unlimited")

    return ValidationReport(ok=not errors, errors=errors, warnings=warnings)


def _validate_entity_bounds(
    label: str, entity: dict[str, Any], spec: InstanceSpec, errors: list[str]
) -> None:
    try:
        x, y, z = entity["x"], entity["y"], entity["z"]
    except KeyError:
        errors.append(f"{label} missing coordinates")
        return
    if not all(type(value) is int for value in (x, y, z)):
        errors.append(f"{label} coordinates must be integers")
        return
    if not (0 <= x < spec.grid.x_size and 0 <= y < spec.grid.y_size and 0 <= z < spec.grid.z_size):
        errors.append(f"{label} is out of grid bounds")


def _validate_height_match(
    label: str, entity: dict[str, Any], height_map: list[list[int]], errors: list[str]
) -> None:
    try:
        expected = height_map[entity["x"]][entity["y"]]
    except (IndexError, KeyError, TypeError):
        errors.append(f"{label} cannot be checked against height_map")
        return
    if entity["z"] != expected:
        errors.append(f"{label} z does not match height_map")


def _validate_matrix(name: str, matrix: Any, expected_size: int, errors: list[str]) -> None:
    if not isinstance(matrix, list) or len(matrix) != expected_size:
        errors.append(f"{name} must be a square {expected_size}x{expected_size} matrix")
        return
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != expected_size:
            errors.append(f"{name} row {i} has invalid length")
            continue
        for j, value in enumerate(row):
            if type(value) not in {int, float} or not math.isfinite(value):
                errors.append(f"{name}[{i}][{j}] must be finite")
            if i == j and abs(value) > 1e-9:
                errors.append(f"{name} diagonal must be zero")


def _box_in_bounds(box: dict[str, Any], spec: InstanceSpec) -> bool:
    required = ["x_min", "y_min", "z_min", "x_max", "y_max", "z_max"]
    if not all(type(box.get(key)) is int for key in required):
        return False
    return (
        0 <= box["x_min"] <= box["x_max"] < spec.grid.x_size
        and 0 <= box["y_min"] <= box["y_max"] < spec.grid.y_size
        and 0 <= box["z_min"] <= box["z_max"] < spec.grid.z_size
    )


def _box_obj(box: dict[str, Any]):
    from data_generator.models import NFZBox

    return NFZBox(
        id=box["id"],
        type=box.get("type", "box"),
        x_min=box["x_min"],
        y_min=box["y_min"],
        z_min=box["z_min"],
        x_max=box["x_max"],
        y_max=box["y_max"],
        z_max=box["z_max"],
    )
