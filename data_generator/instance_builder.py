"""Top-level instance builder."""

from __future__ import annotations

import random
from typing import Any

from data_generator import customers as customers_mod
from data_generator import depot as depot_mod
from data_generator import drone_profile as drone_profile_mod
from data_generator import nfz as nfz_mod
from data_generator import pathfinding
from data_generator import route_feasibility
from data_generator import terrain as terrain_mod
from data_generator.errors import DataGenerationError, GenerationError
from data_generator.models import (
    BaselineRoute,
    Customer,
    Depot,
    DroneProfile,
    InstanceSpec,
    NFZBox,
    TravelMatrices,
    ValidationReport,
)
from data_generator.validator import validate_instance


def build_instance(spec: InstanceSpec) -> tuple[dict[str, Any], ValidationReport]:
    rng = random.Random(spec.generation.random_seed)
    last_error = "no attempts were run"
    last_report: ValidationReport | None = None

    for attempt in range(1, spec.generation.max_full_retries + 1):
        try:
            height_map = terrain_mod.generate_height_map(spec, rng)
            depot = depot_mod.place_depot(spec, height_map)
            if height_map is not None:
                terrain_mod.plateau_around(
                    height_map, depot, spec.terrain.depot_plateau_radius
                )
                depot.z = int(height_map[depot.x, depot.y])

            customers = customers_mod.place_customers(spec, depot, height_map, rng)
            nfzs = nfz_mod.place_nfzs(spec, depot, customers, height_map, rng)
            occupancy = pathfinding.build_occupancy_grid(spec, height_map, nfzs)
            matrices = pathfinding.compute_travel_matrices(
                [depot] + customers, occupancy, spec
            )
            profile = drone_profile_mod.compute_profile(spec, depot, customers, matrices)
            baseline = route_feasibility.build_baseline_routes(
                customers, matrices.costs, matrices.node_ids, profile, spec
            )
            instance = assemble_instance(
                spec=spec,
                height_map=height_map,
                depot=depot,
                customers=customers,
                nfzs=nfzs,
                matrices=matrices,
                profile=profile,
                baseline=baseline,
            )
            report = validate_instance(spec, instance)
            last_report = report
            if report.ok:
                return instance, report
            last_error = "; ".join(report.errors)
        except DataGenerationError as exc:
            last_error = str(exc)
        except Exception as exc:  # pragma: no cover - protects CLI diagnostics.
            last_error = f"unexpected error: {exc}"

        # Advance the deterministic stream differently after each failed attempt.
        rng.random()

    if last_report is not None:
        raise GenerationError(
            f"Failed to generate {spec.instance_name}: {last_error}"
        )
    raise GenerationError(f"Failed to generate {spec.instance_name}: {last_error}")


def assemble_instance(
    spec: InstanceSpec,
    height_map,
    depot: Depot,
    customers: list[Customer],
    nfzs: list[NFZBox],
    matrices: TravelMatrices,
    profile: DroneProfile,
    baseline: list[BaselineRoute],
) -> dict[str, Any]:
    terrain_section: dict[str, Any]
    if height_map is None:
        terrain_section = {
            "enabled": False,
            "x_size": spec.grid.x_size,
            "y_size": spec.grid.y_size,
            "max_height": 0,
            "height_map": None,
        }
    else:
        terrain_section = {
            "enabled": True,
            "x_size": spec.grid.x_size,
            "y_size": spec.grid.y_size,
            "max_height": int(height_map.max()),
            "height_map": height_map.astype(int).tolist(),
        }

    return {
        "metadata": {
            "instance_name": spec.instance_name,
            "size_category": spec.size_category,
            "scenario_type": spec.scenario_type,
            "schema_version": spec.schema_version,
            "random_seed": spec.generation.random_seed,
            "units": dict(spec.units),
            "active_features": {
                "terrain_enabled": spec.feature_flags.terrain_enabled,
                "fleet_size_limited": spec.feature_flags.fleet_size_limited,
                "collision_avoidance": spec.feature_flags.collision_avoidance,
                "explicit_nfz_enabled": spec.feature_flags.explicit_nfz_enabled,
            },
            "grid_bounds": {
                "x_size": spec.grid.x_size,
                "y_size": spec.grid.y_size,
                "z_size": spec.grid.z_size,
            },
            "counts": {
                "customers": len(customers),
                "no_fly_zones": len(nfzs),
            },
        },
        "drone_profile": profile.to_dict(),
        "energy_costs": {
            "horizontal_rate": spec.energy_costs.horizontal_rate,
            "vertical_ascend_multiplier": spec.energy_costs.vertical_ascend_multiplier,
            "vertical_descend_multiplier": spec.energy_costs.vertical_descend_multiplier,
            "hover_rate": spec.energy_costs.hover_rate,
        },
        "pathfinding": {
            "enabled": spec.pathfinding.enabled,
            "algorithm": spec.pathfinding.algorithm,
            "connectivity": spec.pathfinding.connectivity,
            "clearance": spec.pathfinding.clearance,
            "diagonal_cost": spec.pathfinding.diagonal_cost,
            "cache_edge_paths": spec.pathfinding.cache_edge_paths,
            "cost_model": "energy_costs_v1",
        },
        "travel_matrix_node_ids": matrices.node_ids,
        "travel_cost_matrix": matrices.costs,
        "travel_distance_matrix": matrices.distances,
        "terrain": terrain_section,
        "depot": depot.to_dict(),
        "customers": [customer.to_dict() for customer in customers],
        "no_fly_zones": [box.to_dict() for box in nfzs],
        "collision": {
            "enabled": spec.feature_flags.collision_avoidance,
            "safety_distance": (
                spec.collision.safety_distance
                if spec.feature_flags.collision_avoidance
                else None
            ),
        },
        "baseline_feasible_routes": [route.to_dict() for route in baseline],
    }
