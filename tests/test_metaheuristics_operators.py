"""Tests for the operator catalogue (encoding, construction, neighborhood, crossover, mutation)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from metaheuristics.core.evaluator import (
    evaluate_route,
    evaluate_solution,
    is_feasible,
    total_energy,
)
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Route, Solution
from metaheuristics.operators.construction import (
    clarke_wright_savings,
    nearest_neighbor,
    random_split,
)
from metaheuristics.operators.crossover import order_crossover
from metaheuristics.operators.encoding import (
    giant_tour_from_solution,
    split_giant_tour,
)
from metaheuristics.operators.mutation import (
    inversion_mutation,
    relocate_mutation,
    swap_mutation,
)
from metaheuristics.operators.neighborhood import (
    NEIGHBORHOOD_MOVES,
    or_opt_move,
    relocate_move,
    swap_move,
    two_opt_move,
    two_opt_star_move,
)

ROOT = Path(__file__).resolve().parents[1]
SMALL_INSTANCE = ROOT / "data" / "instances" / "instance_01_basic_small.json"


@pytest.fixture(scope="module")
def instance() -> ProblemInstance:
    return ProblemInstance.from_json(SMALL_INSTANCE)


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def test_split_giant_tour_serves_each_customer_once(instance: ProblemInstance) -> None:
    tour = list(instance.customer_ids)
    solution = split_giant_tour(tour, instance)
    assert sorted(solution.all_customers()) == sorted(instance.customer_ids)
    assert is_feasible(solution, instance)


def test_split_optimality_against_baseline(instance: ProblemInstance) -> None:
    baseline_tour = [c for route in instance.baseline_routes for c in route]
    if not baseline_tour:
        pytest.skip("No baseline_feasible_routes in this instance")
    split = split_giant_tour(baseline_tour, instance)
    baseline_solution = Solution.from_lists(instance.baseline_routes)
    assert total_energy(split, instance) <= total_energy(baseline_solution, instance) + 1e-6


def test_giant_tour_roundtrip(instance: ProblemInstance) -> None:
    baseline_solution = Solution.from_lists(instance.baseline_routes)
    tour = giant_tour_from_solution(baseline_solution)
    rebuilt = split_giant_tour(tour, instance)
    assert sorted(rebuilt.all_customers()) == sorted(baseline_solution.all_customers())


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------


def test_nearest_neighbor_produces_feasible_solution(instance: ProblemInstance) -> None:
    rng = random.Random(0)
    solution = nearest_neighbor(instance, rng=rng)
    assert is_feasible(solution, instance)
    assert sorted(solution.all_customers()) == sorted(instance.customer_ids)


def test_savings_produces_feasible_solution(instance: ProblemInstance) -> None:
    solution = clarke_wright_savings(instance)
    assert is_feasible(solution, instance)
    assert sorted(solution.all_customers()) == sorted(instance.customer_ids)


def test_random_split_produces_feasible_solution(instance: ProblemInstance) -> None:
    rng = random.Random(1)
    solution = random_split(instance, rng=rng)
    assert is_feasible(solution, instance)


# ---------------------------------------------------------------------------
# Neighborhood
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "move",
    [swap_move, relocate_move, or_opt_move, two_opt_move, two_opt_star_move],
)
def test_neighborhood_move_preserves_feasibility_or_returns_none(
    instance: ProblemInstance, move
) -> None:
    rng = random.Random(42)
    base = nearest_neighbor(instance, rng=rng)
    # Run a small batch — moves are stochastic and may return None.
    for _ in range(50):
        neighbour = move(base, instance, rng)
        if neighbour is None:
            continue
        assert is_feasible(neighbour, instance), evaluate_solution(neighbour, instance).violations


def test_full_move_registry_is_exposed() -> None:
    assert len(NEIGHBORHOOD_MOVES) == 5


# ---------------------------------------------------------------------------
# Crossover & mutation
# ---------------------------------------------------------------------------


def test_order_crossover_produces_valid_permutations() -> None:
    rng = random.Random(7)
    parent_a = list(range(1, 11))
    parent_b = list(range(1, 11))
    rng.shuffle(parent_b)
    child_a, child_b = order_crossover(parent_a, parent_b, rng)
    assert sorted(child_a) == parent_a
    assert sorted(child_b) == parent_a
    assert len(child_a) == 10


@pytest.mark.parametrize(
    "mutate",
    [swap_mutation, inversion_mutation, relocate_mutation],
)
def test_mutation_preserves_permutation(mutate) -> None:
    rng = random.Random(3)
    chromosome = list(range(1, 11))
    rng.shuffle(chromosome)
    mutated = mutate(chromosome, rng)
    assert sorted(mutated) == sorted(chromosome)
    assert len(mutated) == len(chromosome)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_two_opt_requires_long_routes() -> None:
    """Synthetic micro-test that doesn't touch the loaded instance."""
    rng = random.Random(0)
    solution = Solution(routes=[Route([1, 2])])

    class StubInstance:
        class drone:
            payload_capacity = 100
            battery_capacity = 10_000.0
            fleet_size = None
            fleet_limited = False

        def cost(self, a: int, b: int) -> float:
            return 1.0

        def demand_by_id(self) -> dict[int, int]:  # type: ignore[override]
            return {0: 0, 1: 1, 2: 1}

    # 2-opt needs >= 4 customers; on a 2-customer route it must return None.
    assert two_opt_move(solution, StubInstance(), rng) is None  # type: ignore[arg-type]
