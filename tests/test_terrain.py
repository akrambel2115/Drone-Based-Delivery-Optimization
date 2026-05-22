from __future__ import annotations

import random
from pathlib import Path

import numpy as np

from data_generator.config_loader import load_spec
from data_generator.models import Depot
from data_generator.terrain import generate_height_map, plateau_around

ROOT = Path(__file__).resolve().parents[1]


def test_terrain_is_deterministic_under_fixed_seed() -> None:
    spec = load_spec(
        ROOT / "configs" / "master_config.json",
        ROOT / "configs" / "instance_01_basic_small.json",
    )
    first = generate_height_map(spec, random.Random(spec.generation.random_seed))
    second = generate_height_map(spec, random.Random(spec.generation.random_seed))
    assert first is not None
    assert second is not None
    assert np.array_equal(first, second)
    assert first.shape == (50, 50)


def test_plateau_flattens_depot_disk() -> None:
    height_map = np.arange(25).reshape(5, 5)
    depot = Depot(id=0, x=2, y=2, z=0)
    plateau_around(height_map, depot, radius=1)
    values = [height_map[2, 2], height_map[1, 2], height_map[2, 1], height_map[2, 3], height_map[3, 2]]
    assert len(set(int(value) for value in values)) == 1
