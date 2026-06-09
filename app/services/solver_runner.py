"""Solver orchestration layer: bridges the metaheuristics package to async job management.

Jobs are tracked in an in-memory dict keyed by UUID run_id. Each finished job is also
persisted to data/solver_runs/<run_id>.json for later replay via the history page.

Streaming progress is implemented through a callback injected at the per-plateau (SA) or
per-generation (GA) level via thin subclasses of the solver classes. Callbacks push events
into ``RunJob.progress_events`` — the SSE endpoint drains this list with asyncio polling.
"""

from __future__ import annotations

import dataclasses
import json
import math
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from metaheuristics.algorithms.genetic_algorithm import GAConfig, GeneticAlgorithm
from metaheuristics.algorithms.simulated_annealing import SAConfig, SimulatedAnnealing
from metaheuristics.algorithms.branch_and_bound import BBConfig, BranchAndBound
from metaheuristics.core.evaluator import evaluate_solution, total_energy
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.repair import repair_solution
from metaheuristics.operators.construction import clarke_wright_savings, nearest_neighbor
from metaheuristics.operators.crossover import order_crossover
from metaheuristics.operators.encoding import giant_tour_from_solution, split_giant_tour
from metaheuristics.operators.mutation import inversion_mutation, relocate_mutation, swap_mutation
from metaheuristics.operators.neighborhood import NEIGHBORHOOD_MOVES
from metaheuristics.reporting.result import HistoryEntry, SolveResult, solve_result_to_json

RUNS_DIR = Path("data/solver_runs")
INSTANCES_DIR = Path("data/instances")
EMIT_EVERY_SA = 50
EMIT_EVERY_GA = 1  # every generation

_executor = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class RunJob:
    run_id: str
    status: str  # "running" | "done" | "error"
    instance: str
    algorithm: str
    config: dict[str, Any]
    progress_events: list[dict[str, Any]]
    result: dict[str, Any] | None
    error: str | None
    started_at: float
    finished_at: float | None


_jobs: dict[str, RunJob] = {}


def get_job(run_id: str) -> RunJob | None:
    return _jobs.get(run_id)


def list_jobs() -> list[RunJob]:
    return list(_jobs.values())


# ---------------------------------------------------------------------------
# Streaming SA subclass
# ---------------------------------------------------------------------------


def _accept_worsening_local(delta: float, temperature: float, rng: random.Random) -> bool:
    if temperature <= 0.0:
        return False
    try:
        return rng.random() < math.exp(-delta / temperature)
    except OverflowError:
        return False


class _StreamingSA(SimulatedAnnealing):
    """SA that calls *callback(iteration, best_energy, temperature)* every EMIT_EVERY proposals."""

    def solve_streaming(
        self,
        instance: ProblemInstance,
        callback: Callable[[int, float, float | None], None],
    ) -> SolveResult:
        cfg = self.config
        rng = random.Random(cfg.random_seed)
        start = time.perf_counter()

        if cfg.construction == "savings":
            current = repair_solution(clarke_wright_savings(instance), instance)
        else:
            current = repair_solution(nearest_neighbor(instance, rng=rng), instance)

        current_energy = total_energy(current, instance)
        best = current.clone()
        best_energy = current_energy
        history: list[HistoryEntry] = []

        temperature = cfg.initial_temperature
        total_proposals = 0
        no_improve = 0

        # Emit warm-start energy
        callback(0, best_energy, temperature)

        while temperature > cfg.min_temperature and total_proposals < cfg.max_iterations:
            for _ in range(cfg.inner_iterations):
                if total_proposals >= cfg.max_iterations:
                    break
                total_proposals += 1
                move = rng.choice(self._moves)
                candidate = move(current, instance, rng)
                if candidate is None:
                    continue
                candidate_energy = total_energy(candidate, instance)
                delta = candidate_energy - current_energy

                accepted = False
                if delta < 0 or _accept_worsening_local(delta, temperature, rng):
                    current = candidate
                    current_energy = candidate_energy
                    accepted = True
                    if candidate_energy + 1e-9 < best_energy:
                        best = candidate.clone()
                        best_energy = candidate_energy
                        no_improve = 0
                    else:
                        no_improve += 1
                else:
                    no_improve += 1

                if cfg.record_history:
                    history.append(
                        HistoryEntry(
                            iteration=total_proposals,
                            best_energy=best_energy,
                            current_energy=current_energy,
                            accepted=accepted,
                            temperature=temperature,
                        )
                    )

                if total_proposals % EMIT_EVERY_SA == 0:
                    callback(total_proposals, best_energy, temperature)

                if cfg.no_improvement_window and no_improve >= cfg.no_improvement_window:
                    break

            if cfg.no_improvement_window and no_improve >= cfg.no_improvement_window:
                break
            temperature *= cfg.cooling_rate

        callback(total_proposals, best_energy, temperature)
        runtime = time.perf_counter() - start
        evaluation = evaluate_solution(best, instance)
        return SolveResult(
            algorithm=self.name,
            instance_name=instance.name,
            best_solution=best,
            best_evaluation=evaluation,
            history=history,
            iterations=total_proposals,
            runtime_seconds=runtime,
            config=asdict(cfg),
            notes={"final_temperature": temperature},
        )


# ---------------------------------------------------------------------------
# Streaming GA subclass
# ---------------------------------------------------------------------------


class _StreamingGA(GeneticAlgorithm):
    """GA that calls *callback(generation, best_energy)* after every generation."""

    def solve_streaming(
        self,
        instance: ProblemInstance,
        callback: Callable[[int, float, float | None], None],
    ) -> SolveResult:
        cfg = self.config
        rng = random.Random(cfg.random_seed)
        start = time.perf_counter()

        population = self._seed_population(instance, rng)
        scored = [(self._fitness(chrom, instance), chrom) for chrom in population]
        scored.sort(key=lambda p: p[0])

        best_fitness, best_chromosome = scored[0]
        best_solution = split_giant_tour(best_chromosome, instance)
        history: list[HistoryEntry] = []

        # Emit generation-0 (seed population best)
        callback(0, best_fitness, None)
        if cfg.record_history:
            history.append(HistoryEntry(iteration=0, best_energy=best_fitness, current_energy=best_fitness, accepted=True))

        no_improve_gens = 0
        completed = 0

        for generation in range(1, cfg.generations + 1):
            completed = generation
            next_gen: list[list[int]] = [list(c) for _, c in scored[: cfg.elitism]]

            while len(next_gen) < cfg.population_size:
                pa = self._tournament(scored, rng)
                pb = self._tournament(scored, rng)
                if rng.random() < cfg.crossover_rate:
                    ca, cb = order_crossover(pa, pb, rng)
                else:
                    ca, cb = list(pa), list(pb)
                ca = self._maybe_mutate(ca, rng)
                cb = self._maybe_mutate(cb, rng)
                next_gen.append(ca)
                if len(next_gen) < cfg.population_size:
                    next_gen.append(cb)

            scored = [(self._fitness(c, instance), c) for c in next_gen]
            scored.sort(key=lambda p: p[0])

            cur_best_fitness, cur_best_chrom = scored[0]
            improved = cur_best_fitness + 1e-9 < best_fitness
            if improved:
                best_fitness = cur_best_fitness
                best_chromosome = cur_best_chrom
                best_solution = split_giant_tour(best_chromosome, instance)
                no_improve_gens = 0
            else:
                no_improve_gens += 1

            if cfg.record_history:
                history.append(
                    HistoryEntry(
                        iteration=generation,
                        best_energy=best_fitness,
                        current_energy=cur_best_fitness,
                        accepted=improved,
                    )
                )

            callback(generation, best_fitness, None)

            if cfg.no_improvement_generations and no_improve_gens >= cfg.no_improvement_generations:
                break

        runtime = time.perf_counter() - start
        evaluation = evaluate_solution(best_solution, instance)
        return SolveResult(
            algorithm=self.name,
            instance_name=instance.name,
            best_solution=best_solution,
            best_evaluation=evaluation,
            history=history,
            iterations=completed,
            runtime_seconds=runtime,
            config=asdict(cfg),
            notes={"best_chromosome_length": len(best_chromosome), "raw_fitness": best_fitness},
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def submit_run(instance_name: str, algorithm: str, config: dict[str, Any]) -> str:
    """Queue a solver run and return a fresh run_id."""
    run_id = str(uuid.uuid4())
    job = RunJob(
        run_id=run_id,
        status="running",
        instance=instance_name,
        algorithm=algorithm,
        config=config,
        progress_events=[],
        result=None,
        error=None,
        started_at=time.time(),
        finished_at=None,
    )
    _jobs[run_id] = job
    _executor.submit(_run_solver, job)
    return run_id


def _run_solver(job: RunJob) -> None:
    try:
        instance_path = INSTANCES_DIR / f"{job.instance}.json"
        instance = ProblemInstance.from_json(str(instance_path))

        def callback(iteration: int, best_energy: float, temperature: float | None) -> None:
            job.progress_events.append(
                {
                    "type": "progress",
                    "iteration": iteration,
                    "best_energy": round(best_energy, 4),
                    "temperature": round(temperature, 4) if temperature is not None else None,
                }
            )

        if job.algorithm == "sa":
            sa_cfg = SAConfig(**{k: v for k, v in job.config.items() if k in SAConfig.__dataclass_fields__})
            result = _StreamingSA(sa_cfg).solve_streaming(instance, callback)
        elif job.algorithm == "ga":
            ga_cfg = GAConfig(**{k: v for k, v in job.config.items() if k in GAConfig.__dataclass_fields__})
            result = _StreamingGA(ga_cfg).solve_streaming(instance, callback)
        else:
            bb_cfg = BBConfig(**{k: v for k, v in job.config.items() if k in BBConfig.__dataclass_fields__})
            result = BranchAndBound(bb_cfg).solve_streaming(instance, callback)

        payload = solve_result_to_json(result)

        # Attach run metadata to the persisted file
        payload["run_id"] = job.run_id
        payload["submitted_at"] = job.started_at

        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RUNS_DIR / f"{job.run_id}.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        job.result = payload
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.error = str(exc)
        job.status = "error"
    finally:
        job.finished_at = time.time()
        job.progress_events.append({"type": "done", "iteration": 0, "best_energy": 0.0, "temperature": None})


def load_saved_runs() -> list[dict[str, Any]]:
    """Load run metadata from disk for the history page."""
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            runs.append(data)
        except Exception:  # noqa: BLE001
            pass
    return runs
