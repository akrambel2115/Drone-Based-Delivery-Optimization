"""Explicit no-fly-zone placement."""

from __future__ import annotations

import random

import numpy as np

from data_generator.errors import PlacementError
from data_generator.models import Customer, Depot, InstanceSpec, NFZBox


def place_nfzs(
    spec: InstanceSpec,
    depot: Depot,
    customers: list[Customer],
    height_map: np.ndarray | None,
    rng: random.Random,
) -> list[NFZBox]:
    if not spec.feature_flags.explicit_nfz_enabled or spec.nfz.count == 0:
        return []

    boxes: list[NFZBox] = []
    total_attempts = spec.nfz.max_placement_retries * max(1, spec.nfz.count)
    attempts = 0
    while len(boxes) < spec.nfz.count and attempts < total_attempts:
        attempts += 1
        candidate = _sample_box(spec, height_map, len(boxes) + 1, rng)
        if candidate is None:
            continue
        if _point_touches_box(depot.x, depot.y, depot.z, candidate, margin=1):
            continue
        if any(_point_touches_box(c.x, c.y, c.z, candidate, margin=1) for c in customers):
            continue
        if any(_overlap_ratio(candidate, existing) > spec.nfz.max_overlap_ratio for existing in boxes):
            continue
        boxes.append(candidate)

    if len(boxes) != spec.nfz.count:
        raise PlacementError(
            f"Could not place {spec.nfz.count} NFZ boxes after {total_attempts} attempts"
        )
    return boxes


def _sample_box(
    spec: InstanceSpec,
    height_map: np.ndarray | None,
    box_id: int,
    rng: random.Random,
) -> NFZBox | None:
    dx = rng.randint(spec.nfz.box_size_min, spec.nfz.box_size_max)
    dy = rng.randint(spec.nfz.box_size_min, spec.nfz.box_size_max)
    dz = rng.randint(spec.nfz.height_min, spec.nfz.height_max)
    if dx >= spec.grid.x_size or dy >= spec.grid.y_size:
        return None

    x_min = rng.randrange(0, spec.grid.x_size - dx)
    y_min = rng.randrange(0, spec.grid.y_size - dy)
    x_max = x_min + dx
    y_max = y_min + dy
    cx = min(spec.grid.x_size - 1, max(0, (x_min + x_max) // 2))
    cy = min(spec.grid.y_size - 1, max(0, (y_min + y_max) // 2))
    z_min = int(height_map[cx, cy]) if height_map is not None else 0
    if z_min >= spec.grid.z_size - 1:
        return None
    z_max = min(spec.grid.z_size - 2, z_min + dz)
    if z_max < z_min:
        return None
    return NFZBox(
        id=box_id,
        x_min=x_min,
        y_min=y_min,
        z_min=z_min,
        x_max=x_max,
        y_max=y_max,
        z_max=z_max,
    )


def point_inside_box(x: int, y: int, z: int, box: NFZBox) -> bool:
    return (
        box.x_min <= x <= box.x_max
        and box.y_min <= y <= box.y_max
        and box.z_min <= z <= box.z_max
    )


def boxes_overlap(a: NFZBox, b: NFZBox) -> bool:
    return _intersection_volume(a, b) > 0


def _point_touches_box(x: int, y: int, z: int, box: NFZBox, margin: int) -> bool:
    _ = z
    return (
        box.x_min - margin <= x <= box.x_max + margin
        and box.y_min - margin <= y <= box.y_max + margin
    )


def _overlap_ratio(a: NFZBox, b: NFZBox) -> float:
    intersection = _intersection_volume(a, b)
    if intersection == 0:
        return 0.0
    return intersection / min(_volume(a), _volume(b))


def _intersection_volume(a: NFZBox, b: NFZBox) -> int:
    dx = max(0, min(a.x_max, b.x_max) - max(a.x_min, b.x_min) + 1)
    dy = max(0, min(a.y_max, b.y_max) - max(a.y_min, b.y_min) + 1)
    dz = max(0, min(a.z_max, b.z_max) - max(a.z_min, b.z_min) + 1)
    return dx * dy * dz


def _volume(box: NFZBox) -> int:
    return (
        (box.x_max - box.x_min + 1)
        * (box.y_max - box.y_min + 1)
        * (box.z_max - box.z_min + 1)
    )
