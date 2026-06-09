"""Pydantic models for solver run requests and responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class GAConfigIn(BaseModel):
    population_size: int = Field(40, ge=4, le=500)
    generations: int = Field(200, ge=1, le=2000)
    tournament_size: int = Field(3, ge=2, le=10)
    crossover_rate: float = Field(0.9, ge=0.0, le=1.0)
    mutation_rate: float = Field(0.25, ge=0.0, le=1.0)
    elitism: int = Field(2, ge=0, le=20)
    no_improvement_generations: int = Field(0, ge=0)
    fleet_penalty: float = Field(1000.0, ge=0.0)
    random_seed: int | None = None
    record_history: bool = True


class SAConfigIn(BaseModel):
    initial_temperature: float = Field(100.0, gt=0)
    min_temperature: float = Field(0.05, gt=0)
    cooling_rate: float = Field(0.95, gt=0, lt=1)
    inner_iterations: int = Field(200, ge=1, le=5000)
    max_iterations: int = Field(50_000, ge=100, le=500_000)
    no_improvement_window: int = Field(0, ge=0)
    construction: Literal["nearest_neighbor", "savings"] = "nearest_neighbor"
    random_seed: int | None = None
    record_history: bool = True


class BBConfigIn(BaseModel):
    greedy_initialization: bool = True
    record_history: bool = True


class RunRequest(BaseModel):
    instance: str
    algorithm: Literal["ga", "sa", "bb"]
    config: GAConfigIn | SAConfigIn | BBConfigIn


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class RouteOut(BaseModel):
    drone_id: int
    customers: list[int]


class SolutionOut(BaseModel):
    routes: list[RouteOut]
    depot_zero_array: list[int]


class HistoryEntryOut(BaseModel):
    iteration: int
    best_energy: float
    current_energy: float
    accepted: bool
    temperature: float | None


class RunResult(BaseModel):
    algorithm: str
    instance_name: str
    best_energy: float
    feasible: bool
    num_routes: int
    violations: list[str]
    best_solution: SolutionOut
    iterations: int
    runtime_seconds: float
    config: dict[str, Any]
    notes: dict[str, Any]
    history: list[HistoryEntryOut]


class RunStatus(BaseModel):
    run_id: str
    status: Literal["running", "done", "error"]
    instance: str
    algorithm: str
    progress: int | None = None
    best_energy_so_far: float | None = None
    result: RunResult | None = None
    error: str | None = None
    started_at: float
    finished_at: float | None = None


class RunListItem(BaseModel):
    run_id: str
    instance: str
    algorithm: str
    energy: float | None
    drones: int | None
    runtime: float | None
    ts: float


class ProgressEvent(BaseModel):
    type: Literal["progress", "done", "error"] = "progress"
    iteration: int
    best_energy: float
    temperature: float | None = None
