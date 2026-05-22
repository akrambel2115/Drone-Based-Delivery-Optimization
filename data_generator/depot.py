"""Depot placement."""

from __future__ import annotations

import numpy as np

from data_generator.models import Depot, InstanceSpec


def place_depot(spec: InstanceSpec, height_map: np.ndarray | None) -> Depot:
    if spec.depot.placement == "center":
        x = spec.grid.x_size // 2
        y = spec.grid.y_size // 2
    else:
        if spec.depot.x is None or spec.depot.y is None:
            raise ValueError("explicit depot placement requires x and y")
        x = spec.depot.x
        y = spec.depot.y
    z = int(height_map[x, y]) if height_map is not None else 0
    return Depot(id=0, x=x, y=y, z=z)
