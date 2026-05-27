"""Metaheuristic algorithms (Strategy pattern).

Each algorithm exposes a ``solve(instance) -> SolveResult`` method behind
the :class:`Metaheuristic` interface. The two concrete strategies are:

* :class:`GeneticAlgorithm` — population-based (Task 4a),
* :class:`SimulatedAnnealing` — local-search (Task 4b).
"""

from metaheuristics.algorithms.base import Metaheuristic, SolveResult
from metaheuristics.algorithms.genetic_algorithm import GAConfig, GeneticAlgorithm
from metaheuristics.algorithms.simulated_annealing import SAConfig, SimulatedAnnealing

__all__ = [
    "GAConfig",
    "GeneticAlgorithm",
    "Metaheuristic",
    "SAConfig",
    "SimulatedAnnealing",
    "SolveResult",
]
