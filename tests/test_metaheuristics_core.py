"""Tests for the metaheuristic core layer.

Covers :class:`ProblemInstance`, :class:`Solution`, the evaluator and the
repair operators. The fixtures load a real generated instance to keep the
tests faithful to the production cost model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metaheuristics.core.evaluator import (
    Evaluation,
    evaluate_route,
    evaluate_solution,
    is_feasible,
    route_demand,
    total_energy,
)
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.repair import repair_solution, split_overlong_route
from metaheuristics.core.solution import Route, Solution

ROOT = Path(__file__).resolve().parents[1]
SMALL_INSTANCE = ROOT / "data" / "instances" / "instance_01_basic_small.json"


@pytest.fixture(scope="module")
def small_instance() -> ProblemInstance:
    return ProblemInstance.from_json(SMALL_INSTANCE)


def test_instance_loads_with_expected_invariants(small_instance: ProblemInstance) -> None:
    assert small_instance.depot.id == 0
    assert tuple(c.id for c in small_instance.customers) == small_instance.customer_ids
    assert min(small_instance.customer_ids) == 1
    assert max(small_instance.customer_ids) == small_instance.num_customers
    assert small_instance.cost_matrix[0][0] == 0.0
    assert small_instance.cost(0, 1) == small_instance.cost_matrix[0][1]
    assert len(small_instance.cost_matrix) == small_instance.num_customers + 1


def test_solution_depot_zero_array_roundtrip() -> None:
    original = Solution.from_lists([[1, 2, 3], [4, 5]])
    array = original.to_depot_zero_array()
    assert array == [0, 1, 2, 3, 0, 4, 5, 0]
    rebuilt = Solution.from_depot_zero_array(array)
    assert [route.customers for route in rebuilt.routes] == [
        route.customers for route in original.routes
    ]


def test_evaluate_route_matches_manual_sum(small_instance: ProblemInstance) -> None:
    route_customers = small_instance.baseline_routes[0]
    manual = small_instance.cost(0, route_customers[0])
    for left, right in zip(route_customers, route_customers[1:]):
        manual += small_instance.cost(left, right)
    manual += small_instance.cost(route_customers[-1], 0)
    assert evaluate_route(route_customers, small_instance) == pytest.approx(manual)


def test_baseline_solution_is_feasible(small_instance: ProblemInstance) -> None:
    solution = Solution.from_lists(small_instance.baseline_routes)
    assert is_feasible(solution, small_instance)
    evaluation = evaluate_solution(solution, small_instance)
    assert evaluation.feasible
    assert evaluation.energy == pytest.approx(total_energy(solution, small_instance))


def test_evaluator_flags_duplicate_visits(small_instance: ProblemInstance) -> None:
    cid = small_instance.customer_ids[0]
    solution = Solution(routes=[Route([cid, cid])])
    evaluation = evaluate_solution(solution, small_instance)
    assert not evaluation.feasible
    assert any("duplicate" in v for v in evaluation.violations)


def test_evaluator_flags_missing_customers(small_instance: ProblemInstance) -> None:
    partial = list(small_instance.customer_ids[:-1])
    solution = Solution.from_lists([partial])
    evaluation = evaluate_solution(solution, small_instance)
    assert not evaluation.feasible
    assert any("missing customers" in v for v in evaluation.violations)


def test_split_overlong_route_preserves_order(small_instance: ProblemInstance) -> None:
    all_customers = list(small_instance.customer_ids)
    chunks = split_overlong_route(all_customers, small_instance)
    flat = [c for chunk in chunks for c in chunk]
    assert flat == all_customers
    for chunk in chunks:
        load = sum(small_instance.demand_by_id[c] for c in chunk)
        assert load <= small_instance.drone.payload_capacity
        assert evaluate_route(chunk, small_instance) <= small_instance.drone.battery_capacity + 1e-6


def test_repair_solution_restores_feasibility(small_instance: ProblemInstance) -> None:
    monster = Solution(routes=[Route(list(small_instance.customer_ids))])  # likely infeasible
    repaired = repair_solution(monster, small_instance)
    assert is_feasible(repaired, small_instance)


def test_route_demand_matches_sum(small_instance: ProblemInstance) -> None:
    customers = small_instance.baseline_routes[0]
    assert route_demand(customers, small_instance) == sum(
        small_instance.demand_by_id[c] for c in customers
    )


def test_evaluation_dataclass_round_trip() -> None:
    ev = Evaluation(energy=1.5, feasible=True, num_routes=2, violations=())
    assert ev.penalised_energy == 1.5
