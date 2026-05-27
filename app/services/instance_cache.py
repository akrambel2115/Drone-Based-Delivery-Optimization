"""Lazy cache of instance JSON data indexed by instance name.

Loading is done once per process; the raw dicts are kept in memory so the
API can serve instance summaries and full detail without hitting the disk on
every request.
"""

from __future__ import annotations

import json
from pathlib import Path

INSTANCES_DIR = Path("data/instances")

_cache: dict[str, dict] = {}


def _load_all() -> None:
    for path in sorted(INSTANCES_DIR.glob("instance_*.json")):
        name = path.stem
        if name not in _cache:
            _cache[name] = json.loads(path.read_text(encoding="utf-8"))


def get_all_names() -> list[str]:
    _load_all()
    return list(_cache.keys())


def get_instance(name: str) -> dict | None:
    _load_all()
    return _cache.get(name)


def get_summary(name: str) -> dict | None:
    data = get_instance(name)
    if data is None:
        return None
    meta = data.get("metadata", {})
    drone = data.get("drone_profile", {})
    counts = meta.get("counts", {})
    return {
        "name": name,
        "customers": counts.get("customers", 0),
        "nfzs": counts.get("no_fly_zones", 0),
        "fleet": drone.get("fleet_size"),
        "battery": drone.get("battery_capacity", 0.0),
        "payload": drone.get("payload_capacity", 0),
    }
