"""Reporting utilities for metaheuristic runs.

Encapsulates the run-level data structures (history, best-so-far snapshots,
solver metadata) and their serialisation to JSON. Keeping reporting out of
the algorithm modules makes the solvers easy to test in isolation and lets
external tools (benchmark scripts, dashboards) consume the same artefacts.
"""

from metaheuristics.reporting.result import (
    HistoryEntry,
    SolveResult,
    solve_result_to_json,
)

__all__ = ["HistoryEntry", "SolveResult", "solve_result_to_json"]
