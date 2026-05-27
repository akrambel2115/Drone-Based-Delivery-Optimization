"""Run a metaheuristic solver on a benchmark instance.

The CLI loads a JSON instance, executes the requested solver (``ga`` or
``sa``), prints a one-line summary and optionally writes the full
:class:`SolveResult` to ``--out``.

Examples
--------
Run Simulated Annealing on the smallest benchmark::

    python scripts/solve_metaheuristic.py sa data/instances/instance_01_basic_small.json

Run the Genetic Algorithm with a custom seed and save the report::

    python scripts/solve_metaheuristic.py ga data/instances/instance_02_basic_medium.json \\
        --seed 42 --out data/solver_runs/ga_inst02.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metaheuristics.algorithms.base import Metaheuristic
from metaheuristics.algorithms.genetic_algorithm import GAConfig, GeneticAlgorithm
from metaheuristics.algorithms.simulated_annealing import SAConfig, SimulatedAnnealing
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.reporting.result import SolveResult, write_solve_result


def build_solver(args: argparse.Namespace) -> Metaheuristic:
    if args.solver == "ga":
        config = GAConfig(
            population_size=args.population_size,
            generations=args.generations,
            tournament_size=args.tournament_size,
            crossover_rate=args.crossover_rate,
            mutation_rate=args.mutation_rate,
            elitism=args.elitism,
            no_improvement_generations=args.no_improvement,
            random_seed=args.seed,
            record_history=not args.no_history,
        )
        return GeneticAlgorithm(config)
    if args.solver == "sa":
        config = SAConfig(
            initial_temperature=args.initial_temperature,
            min_temperature=args.min_temperature,
            cooling_rate=args.cooling_rate,
            inner_iterations=args.inner_iterations,
            max_iterations=args.max_iterations,
            no_improvement_window=args.no_improvement,
            construction=args.construction,
            random_seed=args.seed,
            record_history=not args.no_history,
        )
        return SimulatedAnnealing(config)
    raise ValueError(f"Unknown solver: {args.solver}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("solver", choices=["ga", "sa"], help="Metaheuristic to run")
    parser.add_argument("instance", type=Path, help="Path to a generated instance JSON file")
    parser.add_argument("--out", type=Path, default=None, help="Write the full SolveResult here")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--no-history", action="store_true", help="Skip per-iteration history snapshots")

    # GA-specific knobs (ignored if solver=sa)
    ga = parser.add_argument_group("Genetic Algorithm options")
    ga.add_argument("--population-size", type=int, default=GAConfig.population_size)
    ga.add_argument("--generations", type=int, default=GAConfig.generations)
    ga.add_argument("--tournament-size", type=int, default=GAConfig.tournament_size)
    ga.add_argument("--crossover-rate", type=float, default=GAConfig.crossover_rate)
    ga.add_argument("--mutation-rate", type=float, default=GAConfig.mutation_rate)
    ga.add_argument("--elitism", type=int, default=GAConfig.elitism)

    # SA-specific knobs (ignored if solver=ga)
    sa = parser.add_argument_group("Simulated Annealing options")
    sa.add_argument("--initial-temperature", type=float, default=SAConfig.initial_temperature)
    sa.add_argument("--min-temperature", type=float, default=SAConfig.min_temperature)
    sa.add_argument("--cooling-rate", type=float, default=SAConfig.cooling_rate)
    sa.add_argument("--inner-iterations", type=int, default=SAConfig.inner_iterations)
    sa.add_argument("--max-iterations", type=int, default=SAConfig.max_iterations)
    sa.add_argument(
        "--construction",
        choices=["nearest_neighbor", "savings"],
        default=SAConfig.construction,
    )

    parser.add_argument(
        "--no-improvement",
        type=int,
        default=0,
        help="Early-stop after this many non-improving iterations / generations (0 = disable)",
    )
    parser.add_argument(
        "--quiet-routes",
        action="store_true",
        help="Skip the per-route printout (energy/demand/customer list).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    instance_path = args.instance
    if not instance_path.is_absolute():
        instance_path = ROOT / instance_path

    instance = ProblemInstance.from_json(instance_path)
    solver = build_solver(args)
    result: SolveResult = solver.solve(instance)

    print(
        f"[{result.algorithm}] {result.instance_name}: "
        f"energy={result.best_energy:.4f}  routes={result.num_routes}  "
        f"feasible={result.feasible}  iterations={result.iterations}  "
        f"runtime={result.runtime_seconds:.2f}s"
    )
    for violation in result.best_evaluation.violations:
        print(f"  - violation: {violation}")
    if not args.quiet_routes:
        _print_routes(result, instance)
    if args.out is not None:
        out_path = args.out if args.out.is_absolute() else ROOT / args.out
        write_solve_result(result, out_path)
        print(f"  wrote report -> {out_path.relative_to(ROOT)}")
    return 0 if result.feasible else 1


def _print_routes(result: SolveResult, instance: ProblemInstance) -> None:
    """Pretty-print each drone route with its load and energy."""
    from metaheuristics.core.evaluator import evaluate_route

    demand_by_id = instance.demand_by_id
    print("  routes:")
    for route_idx, route in enumerate(result.best_solution.routes, start=1):
        load = sum(demand_by_id[c] for c in route.customers)
        energy = evaluate_route(route.customers, instance)
        path = " -> ".join(["depot"] + [str(c) for c in route.customers] + ["depot"])
        print(
            f"    drone {route_idx}: stops={len(route.customers):<3} "
            f"load={load}/{instance.drone.payload_capacity}  "
            f"energy={energy:.2f}/{instance.drone.battery_capacity}"
        )
        print(f"      path: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
