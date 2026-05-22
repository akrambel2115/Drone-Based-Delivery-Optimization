from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_generator.config_loader import load_spec
from data_generator.errors import ConfigError

ROOT = Path(__file__).resolve().parents[1]


def test_load_spec_merges_instance_over_master() -> None:
    spec = load_spec(
        ROOT / "configs" / "master_config.json",
        ROOT / "configs" / "instance_01_basic_small.json",
    )
    assert spec.instance_name == "instance_01_basic_small"
    assert spec.scenario_type == "basic"
    assert spec.grid.x_size == 50
    assert spec.customers.count == 12
    assert spec.feature_flags.terrain_enabled is True


def test_unknown_config_key_is_rejected(tmp_path: Path) -> None:
    config = json.loads((ROOT / "configs" / "instance_01_basic_small.json").read_text())
    config["customers"]["typo"] = 123
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_spec(ROOT / "configs" / "master_config.json", bad_path)
