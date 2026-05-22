from __future__ import annotations

from pathlib import Path

from data_generator.config_loader import load_spec
from data_generator.instance_builder import build_instance

ROOT = Path(__file__).resolve().parents[1]


def test_baseline_routes_serve_each_customer_once() -> None:
    spec = load_spec(
        ROOT / "configs" / "master_config.json",
        ROOT / "configs" / "instance_04_dense_small.json",
    )
    instance, report = build_instance(spec)
    assert report.ok
    served = [
        customer_id
        for route in instance["baseline_feasible_routes"]
        for customer_id in route["customers"]
    ]
    assert sorted(served) == [customer["id"] for customer in instance["customers"]]
    assert len(instance["baseline_feasible_routes"]) <= instance["drone_profile"]["fleet_size"]
