"""Metaheuristic solvers for the drone-based delivery optimization problem.

The package implements the Task 4 / Task 5 deliverables:

* a Genetic Algorithm (population-based) and a Simulated Annealing
  (local-search) metaheuristic for the multi-drone routing problem,
* problem-specific operators (encoding, construction, neighborhood,
  crossover, mutation, repair).

The public surface mirrors the layered architecture exposed under
``metaheuristics.core``, ``metaheuristics.operators``,
``metaheuristics.algorithms`` and ``metaheuristics.reporting``.

Typical usage::

    from metaheuristics import ProblemInstance, SimulatedAnnealing, SAConfig

    instance = ProblemInstance.from_json("data/instances/instance_01_basic_small.json")
    result = SimulatedAnnealing(SAConfig()).solve(instance)
    print(result.best_energy)

The solvers strictly consume the canonical asymmetric ``travel_cost_matrix``
embedded in every benchmark instance, so they share the exact cost model
used by the exact (Branch-and-Bound) baseline.
"""

from metaheuristics.algorithms.base import Metaheuristic, SolveResult
from metaheuristics.algorithms.genetic_algorithm import GAConfig, GeneticAlgorithm
from metaheuristics.algorithms.simulated_annealing import SAConfig, SimulatedAnnealing
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Route, Solution

__all__ = [
    "GAConfig",
    "GeneticAlgorithm",
    "Metaheuristic",
    "ProblemInstance",
    "Route",
    "SAConfig",
    "SimulatedAnnealing",
    "SolveResult",
    "Solution",
]
