from __future__ import annotations

import json
from pathlib import Path

from data_generator.config_loader import load_spec
from data_generator.instance_builder import build_instance

ROOT = Path(__file__).resolve().parents[1]


def test_all_instance_configs_build_valid_instances() -> None:
    master = ROOT / "configs" / "master_config.json"
    configs = sorted((ROOT / "configs").glob("instance_*.json"))
    assert len(configs) == 10
    for config in configs:
        spec = load_spec(master, config)
        instance, report = build_instance(spec)
        assert report.ok, report.errors
        assert instance["metadata"]["instance_name"] == config.stem
        assert instance["metadata"]["scenario_type"] in {"basic", "dense", "max"}
        assert len(instance["customers"]) == spec.customers.count
        assert len(instance["travel_matrix_node_ids"]) == spec.customers.count + 1
        assert instance["terrain"]["enabled"] is True
        if instance["metadata"]["scenario_type"] == "basic":
            assert instance["no_fly_zones"] == []
        elif instance["metadata"]["scenario_type"] == "dense":
            assert 1 <= len(instance["no_fly_zones"]) <= 2
        else:
            assert 3 <= len(instance["no_fly_zones"]) <= 8


def test_generated_json_matches_schema_if_jsonschema_available() -> None:
    jsonschema = pytest_importorskip_jsonschema()
    schema = json.loads(
        (ROOT / "data_generator" / "schema" / "instance.schema.json").read_text(
            encoding="utf-8"
        )
    )
    instance_path = ROOT / "data" / "instances" / "instance_01_basic_small.json"
    if not instance_path.exists():
        spec = load_spec(
            ROOT / "configs" / "master_config.json",
            ROOT / "configs" / "instance_01_basic_small.json",
        )
        instance, _ = build_instance(spec)
    else:
        instance = json.loads(instance_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def pytest_importorskip_jsonschema():
    import pytest

    return pytest.importorskip("jsonschema")
