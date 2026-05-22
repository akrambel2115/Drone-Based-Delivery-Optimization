"""Energy and distance helpers."""

from __future__ import annotations

import math
from typing import Protocol

from data_generator.models import EnergyCosts


class Point3D(Protocol):
    x: int
    y: int
    z: int


def horizontal_distance(a: Point3D, b: Point3D) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def euclidean_distance(a: Point3D, b: Point3D) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def vertical_distance_cost(dz: float, costs: EnergyCosts) -> float:
    if dz > 0:
        return dz * costs.vertical_ascend_multiplier
    return -dz * costs.vertical_descend_multiplier


def straight_line_energy(a: Point3D, b: Point3D, costs: EnergyCosts) -> float:
    return (
        horizontal_distance(a, b) * costs.horizontal_rate
        + vertical_distance_cost(b.z - a.z, costs)
    )


def segment_energy(
    horizontal: float, dz: float, costs: EnergyCosts, duration: float = 0.0
) -> float:
    return (
        horizontal * costs.horizontal_rate
        + vertical_distance_cost(dz, costs)
        + duration * costs.hover_rate
    )
