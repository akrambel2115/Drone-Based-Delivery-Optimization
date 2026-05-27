"""Run GA and SA on every benchmark instance and emit a comparative report.

The script is a thin orchestrator on top of the metaheuristic library: for
each ``data/instances/instance_*.json`` it instantiates both solvers with
their default :class:`GAConfig` / :class:`SAConfig` (overridable on the
command line), runs them once, and writes a single JSON summary plus a
CSV table ready for plotting in Task 7.

Examples
--------
Run the default sweep::

    python scripts/benchmark_metaheuristics.py

Run with fewer iterations and a fixed seed for reproducibility::

    python scripts/benchmark_metaheuristics.py --seed 7 --ga-generations 50 --sa-max-iterations 5000
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metaheuristics.algorithms.genetic_algorithm import GAConfig, GeneticAlgorithm
from metaheuristics.algorithms.simulated_annealing import SAConfig, SimulatedAnnealing
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.reporting.result import solve_result_to_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--instances-dir",
        type=Path,
        default=ROOT / "data" / "instances",
        help="Directory holding the generated instance JSON files.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "solver_runs",
        help="Directory in which per-run JSON reports and the CSV summary are written.",
    )
    parser.add_argument(
        "--solvers",
        nargs="+",
        choices=["ga", "sa"],
        default=["ga", "sa"],
        help="Which solvers to run on each instance.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Base random seed.")
    parser.add_argument("--ga-population-size", type=int, default=GAConfig.population_size)
    parser.add_argument("--ga-generations", type=int, default=GAConfig.generations)
    parser.add_argument("--sa-initial-temperature", type=float, default=SAConfig.initial_temperature)
    parser.add_argument("--sa-cooling-rate", type=float, default=SAConfig.cooling_rate)
    parser.add_argument("--sa-inner-iterations", type=int, default=SAConfig.inner_iterations)
    parser.add_argument("--sa-max-iterations", type=int, default=SAConfig.max_iterations)
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable per-iteration history recording (cheaper memory).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    instance_paths = sorted(args.instances_dir.glob("instance_*.json"))
    if not instance_paths:
        raise SystemExit(f"No instances found under {args.instances_dir}")

    summary_rows: list[dict[str, object]] = []
    started = time.perf_counter()

    for instance_path in instance_paths:
        instance = ProblemInstance.from_json(instance_path)
        print(f"==> {instance.name} ({instance.num_customers} customers)")
        for solver_name in args.solvers:
            solver, label = _build_solver(solver_name, args)
            result = solver.solve(instance)
            row = {
                "instance": instance.name,
                "customers": instance.num_customers,
                "solver": label,
                "best_energy": result.best_energy,
                "num_routes": result.num_routes,
                "feasible": result.feasible,
                "iterations": result.iterations,
                "runtime_seconds": round(result.runtime_seconds, 4),
            }
            summary_rows.append(row)
            print(
                f"   {label:<22} energy={result.best_energy:.4f}  routes={result.num_routes:<3}  "
                f"feasible={result.feasible}  iter={result.iterations}  "
                f"runtime={result.runtime_seconds:.2f}s"
            )
            report_path = args.out_dir / f"{instance.name}__{label}.json"
            report_path.write_text(
                json.dumps(solve_result_to_json(result), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    summary_path = args.out_dir / "summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    elapsed = time.perf_counter() - started
    print(f"\nDone in {elapsed:.1f}s. Summary -> {summary_path.relative_to(ROOT)}")
    return 0


def _build_solver(solver_name: str, args: argparse.Namespace):
    if solver_name == "ga":
        config = GAConfig(
            population_size=args.ga_population_size,
            generations=args.ga_generations,
            random_seed=args.seed,
            record_history=not args.no_history,
        )
        return GeneticAlgorithm(config), "genetic_algorithm"
    config = SAConfig(
        initial_temperature=args.sa_initial_temperature,
        cooling_rate=args.sa_cooling_rate,
        inner_iterations=args.sa_inner_iterations,
        max_iterations=args.sa_max_iterations,
        random_seed=args.seed,
        record_history=not args.no_history,
    )
    return SimulatedAnnealing(config), "simulated_annealing"


if __name__ == "__main__":
    raise SystemExit(main())
