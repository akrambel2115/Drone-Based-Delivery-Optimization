"""Dataclasses shared by the data-generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeatureFlags:
    terrain_enabled: bool
    fleet_size_limited: bool
    collision_avoidance: bool
    explicit_nfz_enabled: bool


@dataclass(frozen=True)
class GridSpec:
    x_size: int
    y_size: int
    z_size: int


@dataclass(frozen=True)
class TerrainSpec:
    noise_type: str
    octaves: int
    persistence: float
    lacunarity: float
    scale: float
    max_height_ratio: float
    depot_plateau_radius: int


@dataclass(frozen=True)
class DepotSpec:
    placement: str
    x: int | None
    y: int | None


@dataclass(frozen=True)
class CustomersSpec:
    count: int
    demand_min: int
    demand_max: int
    min_separation: int
    max_placement_retries: int


@dataclass(frozen=True)
class NFZSpec:
    count: int
    box_size_min: int
    box_size_max: int
    height_min: int
    height_max: int
    max_overlap_ratio: float
    max_placement_retries: int


@dataclass(frozen=True)
class DroneProfileSpec:
    payload_capacity: int
    battery_capacity: float
    fleet_size: int | None
    auto_size_battery: bool
    auto_size_payload: bool
    battery_slack: float
    target_customers_per_route: int
    fleet_slack: int
    target_payload_utilization_min: float
    target_payload_utilization_max: float
    target_battery_utilization_min: float
    target_battery_utilization_max: float


@dataclass(frozen=True)
class EnergyCosts:
    horizontal_rate: float
    vertical_ascend_multiplier: float
    vertical_descend_multiplier: float
    hover_rate: float


@dataclass(frozen=True)
class PathfindingSpec:
    enabled: bool
    algorithm: str
    connectivity: int
    clearance: int
    diagonal_cost: str
    cache_edge_paths: bool


@dataclass(frozen=True)
class CollisionSpec:
    safety_distance: int


@dataclass(frozen=True)
class GenerationSpec:
    random_seed: int
    max_full_retries: int


@dataclass(frozen=True)
class ExportSpec:
    write_checksum: bool
    write_summary: bool
    write_validation_report: bool


@dataclass(frozen=True)
class InstanceSpec:
    instance_name: str
    size_category: str
    scenario_type: str
    schema_version: str
    units: dict[str, str]
    feature_flags: FeatureFlags
    grid: GridSpec
    terrain: TerrainSpec
    depot: DepotSpec
    customers: CustomersSpec
    nfz: NFZSpec
    drone_profile: DroneProfileSpec
    energy_costs: EnergyCosts
    pathfinding: PathfindingSpec
    collision: CollisionSpec
    generation: GenerationSpec
    export: ExportSpec
    source_config: dict[str, Any]


@dataclass
class Depot:
    id: int
    x: int
    y: int
    z: int

    def to_dict(self) -> dict[str, int]:
        return {"id": self.id, "x": self.x, "y": self.y, "z": self.z}


@dataclass(frozen=True)
class Customer:
    id: int
    x: int
    y: int
    z: int
    demand: int

    def to_dict(self) -> dict[str, int]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "demand": self.demand,
        }


@dataclass(frozen=True)
class NFZBox:
    id: int
    x_min: int
    y_min: int
    z_min: int
    x_max: int
    y_max: int
    z_max: int
    type: str = "box"

    def to_dict(self) -> dict[str, int | str]:
        return {
            "id": self.id,
            "type": self.type,
            "x_min": self.x_min,
            "y_min": self.y_min,
            "z_min": self.z_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "z_max": self.z_max,
        }


@dataclass(frozen=True)
class DroneProfile:
    payload_capacity: int
    battery_capacity: float
    fleet_size: int | None

    def to_dict(self) -> dict[str, int | float | None]:
        return {
            "payload_capacity": self.payload_capacity,
            "battery_capacity": round(self.battery_capacity, 4),
            "fleet_size": self.fleet_size,
        }


@dataclass(frozen=True)
class TravelMatrices:
    node_ids: list[int]
    costs: list[list[float]]
    distances: list[list[float]]


@dataclass(frozen=True)
class BaselineRoute:
    route_id: int
    customers: list[int]
    total_demand: int
    total_energy: float

    def to_dict(self) -> dict[str, int | float | list[int]]:
        return {
            "route_id": self.route_id,
            "customers": list(self.customers),
            "total_demand": self.total_demand,
            "total_energy": round(self.total_energy, 4),
        }


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}
