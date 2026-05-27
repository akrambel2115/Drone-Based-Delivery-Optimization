"""Pydantic models for instance data returned by the /api/instances endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class InstanceSummary(BaseModel):
    name: str
    customers: int
    nfzs: int
    fleet: int | None
    battery: float
    payload: int


class NodeOut(BaseModel):
    id: int
    x: int
    y: int
    z: int
    demand: int


class NFZOut(BaseModel):
    id: int
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    z_min: int
    z_max: int


class TerrainOut(BaseModel):
    enabled: bool
    x_size: int
    y_size: int
    height_map: list[list[float]] | None


class InstanceDetail(BaseModel):
    name: str
    depot: NodeOut
    customers: list[NodeOut]
    no_fly_zones: list[NFZOut]
    terrain: TerrainOut
    drone_profile: dict[str, Any]
    metadata: dict[str, Any]
