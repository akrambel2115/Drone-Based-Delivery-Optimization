"""Simulated Annealing for the drone routing problem.

Algorithm
---------
1. **Initial solution.** Build a feasible solution with the nearest-neighbour
   constructor (or the Clarke-Wright savings heuristic if requested).
2. **Outer loop.** For each *temperature plateau* (``inner_iterations`` moves
   at a fixed temperature ``T``), pick a random neighbourhood move from
   :data:`metaheuristics.operators.NEIGHBORHOOD_MOVES` and evaluate the
   candidate.
3. **Acceptance.** Accept improving moves unconditionally. Accept
   worsening moves with probability ``exp(-Δ / T)`` (Metropolis criterion).
4. **Cooling.** Geometric schedule: ``T <- T * cooling_rate``.
5. **Stop.** When ``T`` falls below ``min_temperature`` or after
   ``max_iterations`` accepted/proposed moves, return the best feasible
   solution observed during the run.

The :class:`SAConfig` carries every knob; the rest of the code is mostly
bookkeeping for the convergence trace.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import asdict, dataclass

from metaheuristics.algorithms.base import Metaheuristic
from metaheuristics.core.evaluator import evaluate_solution, total_energy
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.repair import repair_solution
from metaheuristics.core.solution import Solution
from metaheuristics.operators.construction import (
    clarke_wright_savings,
    nearest_neighbor,
)
from metaheuristics.operators.neighborhood import NEIGHBORHOOD_MOVES, NeighborhoodMove
from metaheuristics.reporting.result import HistoryEntry, SolveResult


@dataclass(frozen=True)
class SAConfig:
    """Simulated Annealing hyper-parameters.

    Attributes
    ----------
    initial_temperature:
        Starting temperature ``T_0``. Choose so the initial acceptance rate
        of worsening moves is in ``[0.5, 0.9]``. With normalised energies in
        the range typical for these instances (tens to thousands of units),
        ``T_0 = 100.0`` works well as a default.
    min_temperature:
        Stopping temperature. Once ``T < min_temperature`` the search ends.
    cooling_rate:
        Geometric cooling factor ``alpha`` with ``T <- alpha * T``.
        Typical range: ``[0.90, 0.999]``. Closer to ``1`` = slower cooling.
    inner_iterations:
        Number of moves attempted at each temperature plateau. Larger values
        increase the chance of escaping local optima at the cost of runtime.
    max_iterations:
        Hard cap on the total number of proposed moves.
    no_improvement_window:
        If positive, stop early when no improving move is accepted within
        this many proposals.
    construction:
        Which constructor seeds the initial solution: ``"nearest_neighbor"``
        or ``"savings"``.
    random_seed:
        Seed for reproducibility. ``None`` lets Python pick one.
    record_history:
        If ``True``, append a :class:`HistoryEntry` for every proposal.
        Disable on very long runs to keep memory bounded.
    """

    initial_temperature: float = 100.0
    min_temperature: float = 0.05
    cooling_rate: float = 0.95
    inner_iterations: int = 200
    max_iterations: int = 50_000
    no_improvement_window: int = 0
    construction: str = "nearest_neighbor"
    random_seed: int | None = None
    record_history: bool = True


class SimulatedAnnealing(Metaheuristic):
    """Local-search metaheuristic (Task 4b deliverable)."""

    name = "simulated_annealing"

    def __init__(self, config: SAConfig | None = None) -> None:
        self.config = config if config is not None else SAConfig()
        self._moves: tuple[NeighborhoodMove, ...] = NEIGHBORHOOD_MOVES

    def solve(self, instance: ProblemInstance) -> SolveResult:
        cfg = self.config
        rng = random.Random(cfg.random_seed)
        start = time.perf_counter()

        current = self._initial_solution(instance, rng)
        current_energy = total_energy(current, instance)
        best = current.clone()
        best_energy = current_energy
        history: list[HistoryEntry] = []

        if cfg.record_history:
            history.append(
                HistoryEntry(
                    iteration=0,
                    best_energy=best_energy,
                    current_energy=current_energy,
                    accepted=True,
                    temperature=cfg.initial_temperature,
                )
            )

        temperature = cfg.initial_temperature
        total_proposals = 0
        iterations_since_improvement = 0

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
                if delta < 0 or _accept_worsening(delta, temperature, rng):
                    current = candidate
                    current_energy = candidate_energy
                    accepted = True
                    if candidate_energy + 1e-9 < best_energy:
                        best = candidate.clone()
                        best_energy = candidate_energy
                        iterations_since_improvement = 0
                    else:
                        iterations_since_improvement += 1
                else:
                    iterations_since_improvement += 1

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

                if cfg.no_improvement_window and iterations_since_improvement >= cfg.no_improvement_window:
                    break

            if cfg.no_improvement_window and iterations_since_improvement >= cfg.no_improvement_window:
                break
            temperature *= cfg.cooling_rate

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

    def _initial_solution(self, instance: ProblemInstance, rng: random.Random) -> Solution:
        if self.config.construction == "savings":
            seed = clarke_wright_savings(instance)
        else:
            seed = nearest_neighbor(instance, rng=rng)
        return repair_solution(seed, instance)


def _accept_worsening(delta: float, temperature: float, rng: random.Random) -> bool:
    """Metropolis acceptance for a worsening move."""
    if temperature <= 0.0:
        return False
    try:
        probability = math.exp(-delta / temperature)
    except OverflowError:  # pragma: no cover - safeguard for huge deltas.
        return False
    return rng.random() < probability
