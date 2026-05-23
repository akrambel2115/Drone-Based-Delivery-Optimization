"""Immutable problem instance loaded from a generated benchmark JSON file.

The data generator emits a JSON file per benchmark instance that already
contains:

* the depot (node ``0``) and the customers (nodes ``1..N``),
* an asymmetric ``travel_cost_matrix`` indexed by ``travel_matrix_node_ids``
  (energy of the obstacle-aware shortest edge, in the canonical cost model),
* an analogous ``travel_distance_matrix`` (geometric distance),
* the drone profile (``payload_capacity``, ``battery_capacity``,
  optional ``fleet_size``).

This module exposes a thin, type-safe view over that JSON. The matrix is kept
as a list of lists for O(1) integer indexing; we also expose a NumPy view for
vectorised operators. Instances are deeply immutable, so they can be shared
between threads or solver processes safely.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class Node:
    """A point of interest in the routing graph (depot or customer).

    Attributes
    ----------
    id:
        Node identifier as stored in the JSON. The depot has ``id == 0``;
        customers have contiguous IDs ``1..N``.
    x, y, z:
        Integer 3D coordinates in grid units.
    demand:
        Payload demand. The depot reports ``0``.
    """

    id: int
    x: int
    y: int
    z: int
    demand: int


@dataclass(frozen=True)
class DroneProfile:
    """Fleet-wide capacity limits."""

    payload_capacity: int
    battery_capacity: float
    fleet_size: int | None

    @property
    def fleet_limited(self) -> bool:
        return self.fleet_size is not None


@dataclass(frozen=True)
class ProblemInstance:
    """Immutable view of a benchmark instance ready for optimisation.

    The instance preserves every constraint that the solver must respect
    (payload, battery, optional fleet size) and exposes the canonical
    asymmetric cost matrix together with a vectorised NumPy view.

    Notes
    -----
    The cost matrix is **asymmetric** whenever the energy model assigns
    different multipliers to vertical ascent and descent (the default).
    Operators that assume symmetric distances (e.g. classical 2-opt) must
    therefore evaluate both directions of the candidate move.
    """

    name: str
    depot: Node
    customers: tuple[Node, ...]
    drone: DroneProfile
    cost_matrix: tuple[tuple[float, ...], ...]
    distance_matrix: tuple[tuple[float, ...], ...]
    node_ids: tuple[int, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    baseline_routes: tuple[tuple[int, ...], ...] = ()

    # --- factory ---------------------------------------------------------

    @classmethod
    def from_json(cls, path: str | Path) -> "ProblemInstance":
        """Load an instance from a generated JSON file."""
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_payload(payload)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProblemInstance":
        """Build an instance from an already-deserialised JSON payload."""
        depot_raw = payload["depot"]
        depot = Node(
            id=int(depot_raw["id"]),
            x=int(depot_raw["x"]),
            y=int(depot_raw["y"]),
            z=int(depot_raw["z"]),
            demand=0,
        )
        customers = tuple(
            Node(
                id=int(c["id"]),
                x=int(c["x"]),
                y=int(c["y"]),
                z=int(c["z"]),
                demand=int(c["demand"]),
            )
            for c in payload["customers"]
        )
        profile_raw = payload["drone_profile"]
        fleet_size = profile_raw.get("fleet_size")
        profile = DroneProfile(
            payload_capacity=int(profile_raw["payload_capacity"]),
            battery_capacity=float(profile_raw["battery_capacity"]),
            fleet_size=int(fleet_size) if fleet_size is not None else None,
        )
        cost_matrix = tuple(tuple(float(v) for v in row) for row in payload["travel_cost_matrix"])
        distance_matrix = tuple(
            tuple(float(v) for v in row) for row in payload["travel_distance_matrix"]
        )
        node_ids = tuple(int(v) for v in payload["travel_matrix_node_ids"])
        return cls(
            name=str(payload["metadata"]["instance_name"]),
            depot=depot,
            customers=customers,
            drone=profile,
            cost_matrix=cost_matrix,
            distance_matrix=distance_matrix,
            node_ids=node_ids,
            metadata=dict(payload["metadata"]),
            baseline_routes=tuple(
                tuple(int(c) for c in route["customers"])
                for route in payload.get("baseline_feasible_routes", [])
            ),
        )

    # --- accessors -------------------------------------------------------

    @property
    def num_customers(self) -> int:
        return len(self.customers)

    @property
    def customer_ids(self) -> tuple[int, ...]:
        return tuple(c.id for c in self.customers)

    @property
    def demand_by_id(self) -> dict[int, int]:
        """Mapping from node ID to demand (depot included with demand 0)."""
        out = {0: 0}
        out.update({c.id: c.demand for c in self.customers})
        return out

    def cost(self, origin: int, destination: int) -> float:
        """Asymmetric travel energy from ``origin`` to ``destination``.

        ``origin`` and ``destination`` are node IDs (``0`` for the depot and
        ``1..N`` for customers). The lookup is O(1) thanks to the validator
        guarantee that customer IDs are contiguous starting at 1.
        """
        return self.cost_matrix[origin][destination]

    def distance(self, origin: int, destination: int) -> float:
        return self.distance_matrix[origin][destination]

    def cost_array(self) -> np.ndarray:
        """Return the cost matrix as a contiguous NumPy array."""
        return np.array(self.cost_matrix, dtype=float)
