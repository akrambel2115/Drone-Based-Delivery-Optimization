"""Strategy-pattern interface for metaheuristic solvers.

Every concrete solver implements :meth:`Metaheuristic.solve` and returns a
fully populated :class:`SolveResult`. Keeping the interface tiny means the
CLI, the benchmark runner and any future comparative tooling can treat
solvers interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from metaheuristics.core.instance import ProblemInstance
from metaheuristics.reporting.result import SolveResult

__all__ = ["Metaheuristic", "SolveResult"]


class Metaheuristic(ABC):
    """Abstract base class for the GA and SA solvers."""

    name: str = "metaheuristic"

    @abstractmethod
    def solve(self, instance: ProblemInstance) -> SolveResult:
        """Run the solver on ``instance`` and return the run report."""
