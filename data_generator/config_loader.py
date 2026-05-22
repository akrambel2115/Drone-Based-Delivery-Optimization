"""Configuration loading, deep merging, and validation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from data_generator.errors import ConfigError
from data_generator.models import (
    CollisionSpec,
    CustomersSpec,
    DepotSpec,
    DroneProfileSpec,
    EnergyCosts,
    ExportSpec,
    FeatureFlags,
    GenerationSpec,
    GridSpec,
    InstanceSpec,
    NFZSpec,
    PathfindingSpec,
    TerrainSpec,
)

_EXTRA_TOP_LEVEL_KEYS = {"instance_name", "size_category", "scenario_type"}


def load_master(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def load_instance(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def load_spec(master_path: str | Path, instance_path: str | Path) -> InstanceSpec:
    master = load_master(master_path)
    instance = load_instance(instance_path)
    _reject_unknown_keys(instance, master)
    return validate(merge(master, instance))


def merge(master: dict[str, Any], instance: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge instance over master without mutating either input."""
    result = copy.deepcopy(master)
    for key, value in instance.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def validate(config: dict[str, Any]) -> InstanceSpec:
    """Validate a merged config and return a normalized dataclass tree."""
    try:
        instance_name = _require_str(config, "instance_name")
        size_category = _require_str(config, "size_category")
        scenario_type = _require_str(config, "scenario_type")
        schema_version = _require_str(config, "schema_version")
        units = _require_dict(config, "units")

        flags_raw = _require_dict(config, "feature_flags")
        grid_raw = _require_dict(config, "grid")
        terrain_raw = _require_dict(config, "terrain")
        depot_raw = _require_dict(config, "depot")
        customers_raw = _require_dict(config, "customers")
        nfz_raw = _require_dict(config, "nfz")
        drone_raw = _require_dict(config, "drone_profile")
        energy_raw = _require_dict(config, "energy_costs")
        path_raw = _require_dict(config, "pathfinding")
        collision_raw = _require_dict(config, "collision")
        generation_raw = _require_dict(config, "generation")
        export_raw = _require_dict(config, "export")

        flags = FeatureFlags(
            terrain_enabled=_as_bool(flags_raw, "terrain_enabled"),
            fleet_size_limited=_as_bool(flags_raw, "fleet_size_limited"),
            collision_avoidance=_as_bool(flags_raw, "collision_avoidance"),
            explicit_nfz_enabled=_as_bool(flags_raw, "explicit_nfz_enabled"),
        )
        grid = GridSpec(
            x_size=_positive_int(grid_raw, "x_size"),
            y_size=_positive_int(grid_raw, "y_size"),
            z_size=_positive_int(grid_raw, "z_size"),
        )
        terrain = TerrainSpec(
            noise_type=_as_str(terrain_raw, "noise_type"),
            octaves=_positive_int(terrain_raw, "octaves"),
            persistence=_range_float(terrain_raw, "persistence", 0.0, 1.0),
            lacunarity=_positive_float(terrain_raw, "lacunarity"),
            scale=_positive_float(terrain_raw, "scale"),
            max_height_ratio=_range_float(terrain_raw, "max_height_ratio", 0.0, 0.95),
            depot_plateau_radius=_nonnegative_int(terrain_raw, "depot_plateau_radius"),
        )
        depot = DepotSpec(
            placement=_as_str(depot_raw, "placement"),
            x=_optional_int(depot_raw, "x"),
            y=_optional_int(depot_raw, "y"),
        )
        customers = CustomersSpec(
            count=_positive_int(customers_raw, "count"),
            demand_min=_positive_int(customers_raw, "demand_min"),
            demand_max=_positive_int(customers_raw, "demand_max"),
            min_separation=_nonnegative_int(customers_raw, "min_separation"),
            max_placement_retries=_positive_int(customers_raw, "max_placement_retries"),
        )
        nfz = NFZSpec(
            count=_nonnegative_int(nfz_raw, "count"),
            box_size_min=_positive_int(nfz_raw, "box_size_min"),
            box_size_max=_positive_int(nfz_raw, "box_size_max"),
            height_min=_positive_int(nfz_raw, "height_min"),
            height_max=_positive_int(nfz_raw, "height_max"),
            max_overlap_ratio=_range_float(nfz_raw, "max_overlap_ratio", 0.0, 1.0),
            max_placement_retries=_positive_int(nfz_raw, "max_placement_retries"),
        )
        drone = DroneProfileSpec(
            payload_capacity=_positive_int(drone_raw, "payload_capacity"),
            battery_capacity=_positive_float(drone_raw, "battery_capacity"),
            fleet_size=_optional_positive_int(drone_raw, "fleet_size"),
            auto_size_battery=_as_bool(drone_raw, "auto_size_battery"),
            auto_size_payload=_as_bool(drone_raw, "auto_size_payload"),
            battery_slack=_positive_float(drone_raw, "battery_slack"),
            target_customers_per_route=_positive_int(
                drone_raw, "target_customers_per_route"
            ),
            fleet_slack=_nonnegative_int(drone_raw, "fleet_slack"),
            target_payload_utilization_min=_range_float(
                drone_raw, "target_payload_utilization_min", 0.0, 1.0
            ),
            target_payload_utilization_max=_range_float(
                drone_raw, "target_payload_utilization_max", 0.0, 1.0
            ),
            target_battery_utilization_min=_range_float(
                drone_raw, "target_battery_utilization_min", 0.0, 1.0
            ),
            target_battery_utilization_max=_range_float(
                drone_raw, "target_battery_utilization_max", 0.0, 1.0
            ),
        )
        energy = EnergyCosts(
            horizontal_rate=_positive_float(energy_raw, "horizontal_rate"),
            vertical_ascend_multiplier=_positive_float(
                energy_raw, "vertical_ascend_multiplier"
            ),
            vertical_descend_multiplier=_positive_float(
                energy_raw, "vertical_descend_multiplier"
            ),
            hover_rate=_nonnegative_float(energy_raw, "hover_rate"),
        )
        pathfinding = PathfindingSpec(
            enabled=_as_bool(path_raw, "enabled"),
            algorithm=_as_str(path_raw, "algorithm"),
            connectivity=_as_int_choice(path_raw, "connectivity", {6, 18, 26}),
            clearance=_nonnegative_int(path_raw, "clearance"),
            diagonal_cost=_as_str(path_raw, "diagonal_cost"),
            cache_edge_paths=_as_bool(path_raw, "cache_edge_paths"),
        )
        collision = CollisionSpec(
            safety_distance=_positive_int(collision_raw, "safety_distance")
        )
        generation = GenerationSpec(
            random_seed=_as_int(generation_raw, "random_seed"),
            max_full_retries=_positive_int(generation_raw, "max_full_retries"),
        )
        export = ExportSpec(
            write_checksum=_as_bool(export_raw, "write_checksum"),
            write_summary=_as_bool(export_raw, "write_summary"),
            write_validation_report=_as_bool(export_raw, "write_validation_report"),
        )
    except KeyError as exc:
        raise ConfigError(f"Missing required key: {exc.args[0]}") from exc

    if size_category not in {"small", "medium", "large"}:
        raise ConfigError("size_category must be one of: small, medium, large")
    if scenario_type not in {"basic", "dense", "max"}:
        raise ConfigError("scenario_type must be one of: basic, dense, max")
    if depot.placement not in {"center", "explicit"}:
        raise ConfigError("depot.placement must be 'center' or 'explicit'")
    if depot.placement == "explicit" and (depot.x is None or depot.y is None):
        raise ConfigError("explicit depot placement requires depot.x and depot.y")
    if depot.x is not None and not (0 <= depot.x < grid.x_size):
        raise ConfigError("depot.x is outside grid bounds")
    if depot.y is not None and not (0 <= depot.y < grid.y_size):
        raise ConfigError("depot.y is outside grid bounds")
    if customers.demand_min > customers.demand_max:
        raise ConfigError("customers.demand_min cannot exceed demand_max")
    if nfz.box_size_min > nfz.box_size_max:
        raise ConfigError("nfz.box_size_min cannot exceed box_size_max")
    if nfz.height_min > nfz.height_max:
        raise ConfigError("nfz.height_min cannot exceed height_max")
    if flags.terrain_enabled or flags.explicit_nfz_enabled:
        if not pathfinding.enabled:
            raise ConfigError(
                "pathfinding.enabled cannot be false when terrain or explicit NFZs are enabled"
            )
    if flags.fleet_size_limited and drone.fleet_size is not None and drone.fleet_size < 1:
        raise ConfigError("fleet-limited instances require fleet_size >= 1")
    if drone.target_payload_utilization_min > drone.target_payload_utilization_max:
        raise ConfigError("payload utilization min cannot exceed max")
    if drone.target_battery_utilization_min > drone.target_battery_utilization_max:
        raise ConfigError("battery utilization min cannot exceed max")
    if not all(isinstance(value, str) for value in units.values()):
        raise ConfigError("units must be a string-valued object")

    return InstanceSpec(
        instance_name=instance_name,
        size_category=size_category,
        scenario_type=scenario_type,
        schema_version=schema_version,
        units=dict(units),
        feature_flags=flags,
        grid=grid,
        terrain=terrain,
        depot=depot,
        customers=customers,
        nfz=nfz,
        drone_profile=drone,
        energy_costs=energy,
        pathfinding=pathfinding,
        collision=collision,
        generation=generation,
        export=export,
        source_config=copy.deepcopy(config),
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    return data


def _reject_unknown_keys(
    instance: dict[str, Any], master: dict[str, Any], prefix: str = ""
) -> None:
    for key, value in instance.items():
        if prefix == "" and key in _EXTRA_TOP_LEVEL_KEYS:
            continue
        if key not in master:
            path = f"{prefix}.{key}" if prefix else key
            raise ConfigError(f"Unknown config key: {path}")
        if isinstance(value, dict) and isinstance(master[key], dict):
            child_prefix = f"{prefix}.{key}" if prefix else key
            _reject_unknown_keys(value, master[key], child_prefix)


def _require_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data[key]
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be an object")
    return value


def _require_str(data: dict[str, Any], key: str) -> str:
    return _as_str(data, key)


def _as_str(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{key} must be a non-empty string")
    return value


def _as_bool(data: dict[str, Any], key: str) -> bool:
    value = data[key]
    if type(value) is not bool:
        raise ConfigError(f"{key} must be a boolean")
    return value


def _as_int(data: dict[str, Any], key: str) -> int:
    value = data[key]
    if type(value) is not int:
        raise ConfigError(f"{key} must be an integer")
    return value


def _optional_int(data: dict[str, Any], key: str) -> int | None:
    value = data[key]
    if value is None:
        return None
    if type(value) is not int:
        raise ConfigError(f"{key} must be an integer or null")
    return value


def _optional_positive_int(data: dict[str, Any], key: str) -> int | None:
    value = _optional_int(data, key)
    if value is not None and value <= 0:
        raise ConfigError(f"{key} must be positive or null")
    return value


def _positive_int(data: dict[str, Any], key: str) -> int:
    value = _as_int(data, key)
    if value <= 0:
        raise ConfigError(f"{key} must be positive")
    return value


def _nonnegative_int(data: dict[str, Any], key: str) -> int:
    value = _as_int(data, key)
    if value < 0:
        raise ConfigError(f"{key} must be non-negative")
    return value


def _positive_float(data: dict[str, Any], key: str) -> float:
    value = data[key]
    if type(value) not in {int, float} or value <= 0:
        raise ConfigError(f"{key} must be a positive number")
    return float(value)


def _nonnegative_float(data: dict[str, Any], key: str) -> float:
    value = data[key]
    if type(value) not in {int, float} or value < 0:
        raise ConfigError(f"{key} must be a non-negative number")
    return float(value)


def _range_float(data: dict[str, Any], key: str, lower: float, upper: float) -> float:
    value = data[key]
    if type(value) not in {int, float}:
        raise ConfigError(f"{key} must be numeric")
    value = float(value)
    if not (lower <= value <= upper):
        raise ConfigError(f"{key} must be in [{lower}, {upper}]")
    return value


def _as_int_choice(data: dict[str, Any], key: str, choices: set[int]) -> int:
    value = _as_int(data, key)
    if value not in choices:
        raise ConfigError(f"{key} must be one of {sorted(choices)}")
    return value
