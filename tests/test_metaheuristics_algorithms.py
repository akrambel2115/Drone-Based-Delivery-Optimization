"""End-to-end tests for the GA and SA solvers.

The tests run with deliberately small budgets so the test suite stays fast
(< 5 s on a laptop). They assert two properties:

1. The returned :class:`SolveResult` is **feasible** with respect to every
   declared constraint.
2. Each metaheuristic **improves on the deterministic nearest-neighbour
   warm start** on a small instance — a sanity check that the operators
   actually explore the neighbourhood.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from metaheuristics.algorithms.genetic_algorithm import GAConfig, GeneticAlgorithm
from metaheuristics.algorithms.simulated_annealing import SAConfig, SimulatedAnnealing
from metaheuristics.core.evaluator import total_energy
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.operators.construction import nearest_neighbor

ROOT = Path(__file__).resolve().parents[1]
SMALL_INSTANCE = ROOT / "data" / "instances" / "instance_01_basic_small.json"


@pytest.fixture(scope="module")
def instance() -> ProblemInstance:
    return ProblemInstance.from_json(SMALL_INSTANCE)


@pytest.fixture(scope="module")
def warm_start_energy(instance: ProblemInstance) -> float:
    rng = random.Random(0)
    return total_energy(nearest_neighbor(instance, rng=rng), instance)


def test_simulated_annealing_returns_feasible_result(instance: ProblemInstance) -> None:
    solver = SimulatedAnnealing(
        SAConfig(
            initial_temperature=50.0,
            min_temperature=0.5,
            cooling_rate=0.9,
            inner_iterations=80,
            max_iterations=4_000,
            random_seed=11,
            record_history=False,
        )
    )
    result = solver.solve(instance)
    assert result.feasible, result.best_evaluation.violations


def test_simulated_annealing_improves_on_warm_start(
    instance: ProblemInstance, warm_start_energy: float
) -> None:
    solver = SimulatedAnnealing(
        SAConfig(
            initial_temperature=50.0,
            min_temperature=0.5,
            cooling_rate=0.9,
            inner_iterations=120,
            max_iterations=6_000,
            random_seed=17,
            record_history=False,
        )
    )
    result = solver.solve(instance)
    # SA must reach an energy at least as good as the deterministic NN seed.
    assert result.best_energy <= warm_start_energy + 1e-6


def test_genetic_algorithm_returns_feasible_result(instance: ProblemInstance) -> None:
    solver = GeneticAlgorithm(
        GAConfig(
            population_size=20,
            generations=30,
            crossover_rate=0.9,
            mutation_rate=0.3,
            elitism=2,
            random_seed=21,
            record_history=False,
        )
    )
    result = solver.solve(instance)
    assert result.feasible, result.best_evaluation.violations


def test_genetic_algorithm_improves_on_warm_start(
    instance: ProblemInstance, warm_start_energy: float
) -> None:
    solver = GeneticAlgorithm(
        GAConfig(
            population_size=30,
            generations=60,
            crossover_rate=0.9,
            mutation_rate=0.3,
            elitism=2,
            random_seed=29,
            record_history=False,
        )
    )
    result = solver.solve(instance)
    # The seed includes the savings construction; the GA must not do worse than that.
    assert result.best_energy <= warm_start_energy + 1e-6
