"""Canonical obstacle-aware travel matrices.

The generator first uses direct segments when they are clear. If a direct segment
crosses terrain or an explicit no-fly zone, it uses a deterministic
ascend-cruise-descend path above all generated obstacles. This keeps benchmark
generation fast for large instances while preserving one shared obstacle-aware
cost model for every solver.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

from data_generator.energy import euclidean_distance, segment_energy, straight_line_energy
from data_generator.errors import PathfindingError
from data_generator.models import Customer, Depot, InstanceSpec, NFZBox, TravelMatrices

Node = Depot | Customer


@dataclass(frozen=True)
class PathResult:
    cost: float
    distance: float
    mode: str


@dataclass(frozen=True)
class OccupancyGrid:
    x_size: int
    y_size: int
    z_size: int
    height_map: np.ndarray | None
    nfzs: list[NFZBox]
    clearance: int = 0

    def is_occupied(self, x: int, y: int, z: int) -> bool:
        if x < 0 or y < 0 or z < 0:
            return True
        if x >= self.x_size or y >= self.y_size or z >= self.z_size:
            return True
        if self.height_map is not None and z < int(self.height_map[x, y]) + self.clearance:
            return True
        for box in self.nfzs:
            if (
                box.x_min - self.clearance <= x <= box.x_max + self.clearance
                and box.y_min - self.clearance <= y <= box.y_max + self.clearance
                and box.z_min - self.clearance <= z <= box.z_max + self.clearance
            ):
                return True
        return False

    def safe_cruise_altitude(self, a: Node, b: Node) -> int:
        highest = max(a.z, b.z)
        if self.height_map is not None:
            highest = max(highest, int(np.max(self.height_map)) + self.clearance)
        for box in self.nfzs:
            highest = max(highest, box.z_max + 1 + self.clearance)
        if highest >= self.z_size:
            raise PathfindingError("No safe cruise altitude exists within z bounds")
        return highest


def build_occupancy_grid(
    spec: InstanceSpec, height_map: np.ndarray | None, nfzs: list[NFZBox]
) -> OccupancyGrid:
    return OccupancyGrid(
        x_size=spec.grid.x_size,
        y_size=spec.grid.y_size,
        z_size=spec.grid.z_size,
        height_map=height_map,
        nfzs=nfzs,
        clearance=spec.pathfinding.clearance,
    )


def compute_travel_matrices(
    nodes: Sequence[Node], occupancy_grid: OccupancyGrid, spec: InstanceSpec
) -> TravelMatrices:
    node_ids = [node.id for node in nodes]
    n = len(nodes)
    costs = [[0.0 for _ in range(n)] for _ in range(n)]
    distances = [[0.0 for _ in range(n)] for _ in range(n)]

    for i, origin in enumerate(nodes):
        for j, destination in enumerate(nodes):
            if i == j:
                continue
            result = edge_cost(origin, destination, occupancy_grid, spec)
            costs[i][j] = round(result.cost, 4)
            distances[i][j] = round(result.distance, 4)
    return TravelMatrices(node_ids=node_ids, costs=costs, distances=distances)


def edge_cost(a: Node, b: Node, occupancy_grid: OccupancyGrid, spec: InstanceSpec) -> PathResult:
    if a.id == b.id:
        return PathResult(cost=0.0, distance=0.0, mode="same_node")

    if not spec.pathfinding.enabled or _segment_clear(a, b, occupancy_grid):
        return PathResult(
            cost=straight_line_energy(a, b, spec.energy_costs),
            distance=euclidean_distance(a, b),
            mode="direct",
        )

    cruise_z = occupancy_grid.safe_cruise_altitude(a, b)
    up = _PseudoNode(a.x, a.y, cruise_z)
    across = _PseudoNode(b.x, b.y, cruise_z)
    if not (
        _segment_clear(a, up, occupancy_grid)
        and _segment_clear(up, across, occupancy_grid)
        and _segment_clear(across, b, occupancy_grid)
    ):
        raise PathfindingError(
            f"No obstacle-aware safe-altitude path from node {a.id} to {b.id}"
        )

    horizontal = math.hypot(a.x - b.x, a.y - b.y)
    cost = (
        segment_energy(0.0, cruise_z - a.z, spec.energy_costs)
        + segment_energy(horizontal, 0.0, spec.energy_costs)
        + segment_energy(0.0, b.z - cruise_z, spec.energy_costs)
    )
    distance = abs(cruise_z - a.z) + horizontal + abs(cruise_z - b.z)
    return PathResult(cost=cost, distance=distance, mode="safe_altitude")


def _segment_clear(a: Node | "_PseudoNode", b: Node | "_PseudoNode", grid: OccupancyGrid) -> bool:
    dx = b.x - a.x
    dy = b.y - a.y
    dz = b.z - a.z
    samples = max(2, int(max(abs(dx), abs(dy), abs(dz)) * 2) + 1)
    for step in range(samples + 1):
        t = step / samples
        x = int(round(a.x + dx * t))
        y = int(round(a.y + dy * t))
        z = int(round(a.z + dz * t))
        if grid.is_occupied(x, y, z):
            return False
    return True


@dataclass(frozen=True)
class _PseudoNode:
    x: int
    y: int
    z: int
