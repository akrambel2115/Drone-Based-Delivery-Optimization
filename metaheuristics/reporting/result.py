"""Result objects produced by every metaheuristic.

The :class:`SolveResult` carries:

* the best feasible solution found,
* the objective value (total energy),
* the convergence history (best-so-far energy over iterations),
* wall-clock runtime and iteration count,
* the solver name and the snapshot of its configuration.

JSON serialisation is deliberately verbose so that downstream comparative
analysis (Task 7) can replay results without re-running the solvers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from metaheuristics.core.evaluator import Evaluation
from metaheuristics.core.solution import Solution


@dataclass(frozen=True)
class HistoryEntry:
    """One snapshot of the optimisation trajectory."""

    iteration: int
    best_energy: float
    current_energy: float
    accepted: bool = True
    temperature: float | None = None


@dataclass
class SolveResult:
    """Full report produced by a metaheuristic ``solve`` call."""

    algorithm: str
    instance_name: str
    best_solution: Solution
    best_evaluation: Evaluation
    history: list[HistoryEntry] = field(default_factory=list)
    iterations: int = 0
    runtime_seconds: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def best_energy(self) -> float:
        return self.best_evaluation.energy

    @property
    def feasible(self) -> bool:
        return self.best_evaluation.feasible

    @property
    def num_routes(self) -> int:
        return self.best_evaluation.num_routes


def solve_result_to_json(result: SolveResult) -> dict[str, Any]:
    """Convert a :class:`SolveResult` to a plain JSON-serialisable dict."""
    return {
        "algorithm": result.algorithm,
        "instance_name": result.instance_name,
        "best_energy": round(result.best_energy, 6),
        "feasible": result.feasible,
        "num_routes": result.num_routes,
        "violations": list(result.best_evaluation.violations),
        "best_solution": {
            "routes": [
                {"customers": list(route.customers)} for route in result.best_solution.routes
            ],
            "depot_zero_array": result.best_solution.to_depot_zero_array(),
        },
        "iterations": result.iterations,
        "runtime_seconds": round(result.runtime_seconds, 6),
        "config": result.config,
        "notes": result.notes,
        "history": [asdict(entry) for entry in result.history],
    }


def write_solve_result(result: SolveResult, path: str | Path) -> Path:
    """Serialise a :class:`SolveResult` to ``path`` and return the path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(solve_result_to_json(result), indent=2, ensure_ascii=False)
    out.write_text(payload + "\n", encoding="utf-8")
    return out
