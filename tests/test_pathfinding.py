from __future__ import annotations

from pathlib import Path

from data_generator.config_loader import load_spec
from data_generator.models import Customer, Depot, NFZBox
from data_generator.pathfinding import build_occupancy_grid, edge_cost

ROOT = Path(__file__).resolve().parents[1]


def test_edge_uses_safe_altitude_when_direct_segment_crosses_nfz() -> None:
    spec = load_spec(
        ROOT / "configs" / "master_config.json",
        ROOT / "configs" / "instance_04_dense_small.json",
    )
    depot = Depot(id=0, x=0, y=5, z=0)
    customer = Customer(id=1, x=10, y=5, z=0, demand=1)
    nfz = NFZBox(id=1, x_min=4, y_min=4, z_min=0, x_max=6, y_max=6, z_max=5)
    occupancy = build_occupancy_grid(spec, None, [nfz])
    result = edge_cost(depot, customer, occupancy, spec)
    assert result.mode == "safe_altitude"
    assert result.cost > 10.0
