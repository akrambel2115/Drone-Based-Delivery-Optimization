"""Terrain height-map generation."""

from __future__ import annotations

import math
import random

import numpy as np

from data_generator.models import Depot, InstanceSpec


def generate_height_map(spec: InstanceSpec, rng: random.Random) -> np.ndarray | None:
    if not spec.feature_flags.terrain_enabled:
        return None

    x_size = spec.grid.x_size
    y_size = spec.grid.y_size
    max_height = max(1, int(math.floor(spec.grid.z_size * spec.terrain.max_height_ratio)))

    xs = np.arange(x_size, dtype=float)[:, None]
    ys = np.arange(y_size, dtype=float)[None, :]
    field = np.zeros((x_size, y_size), dtype=float)

    amplitude = 1.0
    frequency = 1.0 / spec.terrain.scale
    for _ in range(spec.terrain.octaves):
        phase_x = rng.random() * 2.0 * math.pi
        phase_y = rng.random() * 2.0 * math.pi
        phase_xy = rng.random() * 2.0 * math.pi
        layer = (
            np.sin((xs * frequency) + phase_x)
            + np.cos((ys * frequency) + phase_y)
            + np.sin(((xs + ys) * frequency * 0.7) + phase_xy)
        ) / 3.0
        field += amplitude * layer
        amplitude *= spec.terrain.persistence
        frequency *= spec.terrain.lacunarity

    field -= float(field.min())
    peak = float(field.max())
    if peak > 0:
        field /= peak
    height_map = np.floor(field * max_height).astype(int)
    return height_map


def plateau_around(height_map: np.ndarray, depot: Depot, radius: int) -> None:
    if radius <= 0:
        return
    xs: list[int] = []
    ys: list[int] = []
    for x in range(max(0, depot.x - radius), min(height_map.shape[0], depot.x + radius + 1)):
        for y in range(
            max(0, depot.y - radius), min(height_map.shape[1], depot.y + radius + 1)
        ):
            if (x - depot.x) ** 2 + (y - depot.y) ** 2 <= radius**2:
                xs.append(x)
                ys.append(y)
    if not xs:
        return
    median_height = int(np.median(height_map[xs, ys]))
    height_map[xs, ys] = median_height


def solid(height_map: np.ndarray | None, x: int, y: int, z: int) -> bool:
    if height_map is None:
        return z < 0
    return z < int(height_map[x, y])
