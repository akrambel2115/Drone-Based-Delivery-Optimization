"""Core domain layer for the metaheuristic solvers.

Modules
-------
instance
    Immutable :class:`ProblemInstance` loaded from a generated benchmark JSON.
solution
    :class:`Route` and :class:`Solution` value objects (the canonical
    list-of-routes representation).
evaluator
    Pure functions that compute energy and feasibility from a cost matrix.
repair
    Operators that take an arbitrary route partition and restore feasibility
    with respect to payload and battery constraints.
"""

from metaheuristics.core.evaluator import (
    Evaluation,
    evaluate_route,
    evaluate_solution,
    is_feasible,
    total_energy,
)
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.repair import repair_solution, split_overlong_route
from metaheuristics.core.solution import Route, Solution

__all__ = [
    "Evaluation",
    "ProblemInstance",
    "Route",
    "Solution",
    "evaluate_route",
    "evaluate_solution",
    "is_feasible",
    "repair_solution",
    "split_overlong_route",
    "total_energy",
]
