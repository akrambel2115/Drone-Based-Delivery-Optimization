"""Genetic Algorithm for the drone routing problem.

Encoding
--------
Each chromosome is a permutation of the customer IDs (the *giant tour*).
Decoding to a feasible routes-list is delegated to Prins'
:func:`metaheuristics.operators.encoding.split_giant_tour`, which is the
optimal partition of the permutation under payload and battery limits.
Therefore every chromosome corresponds to a feasible solution (or to an
infeasible-with-respect-to-fleet-size one, which is penalised below).

Search loop
-----------
1. **Initialisation.** Seed the population with the Clarke-Wright savings
   tour, the nearest-neighbour tour and a baseline tour (the certificate
   shipped in the JSON instance), then fill the remaining slots with random
   permutations. Identical chromosomes are tolerated; the operators inject
   diversity quickly.
2. **Selection.** Tournament selection of size :pyattr:`GAConfig.tournament_size`.
3. **Recombination.** :func:`order_crossover` with probability
   :pyattr:`GAConfig.crossover_rate`.
4. **Mutation.** One of swap / inversion / relocate, chosen uniformly,
   applied with probability :pyattr:`GAConfig.mutation_rate`.
5. **Replacement.** Generational with elitism — the
   :pyattr:`GAConfig.elitism` best chromosomes are carried over unchanged.
6. **Stop.** After :pyattr:`GAConfig.generations` generations or once
   :pyattr:`GAConfig.no_improvement_generations` of stagnation are reached.

Fitness
-------
Fitness is the **total energy** returned by Split, plus a soft penalty
when the partition exceeds the optional fleet-size limit. This keeps the
genetic operators ignorant of constraints and concentrates feasibility
logic in one place (the decoder + a single penalty term).
"""

from __future__ import annotations

import random
import time
from dataclasses import asdict, dataclass

from metaheuristics.algorithms.base import Metaheuristic
from metaheuristics.core.evaluator import evaluate_solution, total_energy
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Solution
from metaheuristics.operators.construction import (
    clarke_wright_savings,
    nearest_neighbor,
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
from metaheuristics.reporting.result import HistoryEntry, SolveResult


@dataclass(frozen=True)
class GAConfig:
    """Genetic Algorithm hyper-parameters.

    Attributes
    ----------
    population_size:
        Number of chromosomes carried between generations. The seed
        injects three deterministic individuals (savings, NN, baseline); the
        remaining ``population_size - 3`` chromosomes are random permutations.
    generations:
        Maximum number of generations.
    tournament_size:
        Size of the selection tournament. ``2``-``5`` is typical.
    crossover_rate:
        Probability of applying :func:`order_crossover` to a parent pair.
        Otherwise, the parents are cloned into the next generation as is.
    mutation_rate:
        Probability of applying one mutation operator to each offspring.
    elitism:
        Number of best chromosomes copied verbatim into the next generation.
    no_improvement_generations:
        Stop early when the best fitness has not improved for this many
        generations. Set to ``0`` to disable.
    fleet_penalty:
        Multiplier applied to ``(num_routes - fleet_size)`` when the
        chromosome decodes to more routes than the drone fleet allows.
        Only used on fleet-limited instances.
    random_seed:
        Seed for reproducibility. ``None`` lets Python pick one.
    record_history:
        If ``True``, append a :class:`HistoryEntry` per generation.
    """

    population_size: int = 40
    generations: int = 200
    tournament_size: int = 3
    crossover_rate: float = 0.9
    mutation_rate: float = 0.25
    elitism: int = 2
    no_improvement_generations: int = 0
    fleet_penalty: float = 1_000.0
    random_seed: int | None = None
    record_history: bool = True


class GeneticAlgorithm(Metaheuristic):
    """Population-based metaheuristic (Task 4a deliverable)."""

    name = "genetic_algorithm"

    def __init__(self, config: GAConfig | None = None) -> None:
        self.config = config if config is not None else GAConfig()
        self._mutation_operators = (swap_mutation, inversion_mutation, relocate_mutation)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def solve(self, instance: ProblemInstance) -> SolveResult:
        cfg = self.config
        rng = random.Random(cfg.random_seed)
        start = time.perf_counter()

        population = self._seed_population(instance, rng)
        scored = [(self._fitness(chrom, instance), chrom) for chrom in population]
        scored.sort(key=lambda pair: pair[0])

        best_fitness, best_chromosome = scored[0]
        best_solution = split_giant_tour(best_chromosome, instance)
        history: list[HistoryEntry] = []
        if cfg.record_history:
            history.append(
                HistoryEntry(
                    iteration=0,
                    best_energy=best_fitness,
                    current_energy=best_fitness,
                    accepted=True,
                )
            )

        generations_without_improvement = 0
        completed_generations = 0

        for generation in range(1, cfg.generations + 1):
            completed_generations = generation
            next_generation: list[list[int]] = [list(chrom) for _, chrom in scored[: cfg.elitism]]

            while len(next_generation) < cfg.population_size:
                parent_a = self._tournament(scored, rng)
                parent_b = self._tournament(scored, rng)
                if rng.random() < cfg.crossover_rate:
                    child_a, child_b = order_crossover(parent_a, parent_b, rng)
                else:
                    child_a, child_b = list(parent_a), list(parent_b)
                child_a = self._maybe_mutate(child_a, rng)
                child_b = self._maybe_mutate(child_b, rng)
                next_generation.append(child_a)
                if len(next_generation) < cfg.population_size:
                    next_generation.append(child_b)

            scored = [(self._fitness(chrom, instance), chrom) for chrom in next_generation]
            scored.sort(key=lambda pair: pair[0])

            current_best_fitness, current_best_chromosome = scored[0]
            improvement = current_best_fitness + 1e-9 < best_fitness
            if improvement:
                best_fitness = current_best_fitness
                best_chromosome = current_best_chromosome
                best_solution = split_giant_tour(best_chromosome, instance)
                generations_without_improvement = 0
            else:
                generations_without_improvement += 1

            if cfg.record_history:
                history.append(
                    HistoryEntry(
                        iteration=generation,
                        best_energy=best_fitness,
                        current_energy=current_best_fitness,
                        accepted=improvement,
                    )
                )

            if (
                cfg.no_improvement_generations
                and generations_without_improvement >= cfg.no_improvement_generations
            ):
                break

        runtime = time.perf_counter() - start
        evaluation = evaluate_solution(best_solution, instance)
        return SolveResult(
            algorithm=self.name,
            instance_name=instance.name,
            best_solution=best_solution,
            best_evaluation=evaluation,
            history=history,
            iterations=completed_generations,
            runtime_seconds=runtime,
            config=asdict(cfg),
            notes={
                "best_chromosome_length": len(best_chromosome),
                "raw_fitness": best_fitness,
            },
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _seed_population(
        self, instance: ProblemInstance, rng: random.Random
    ) -> list[list[int]]:
        customer_ids = list(instance.customer_ids)
        cfg = self.config
        population: list[list[int]] = []

        try:
            savings = clarke_wright_savings(instance)
            population.append(giant_tour_from_solution(savings))
        except Exception:  # pragma: no cover - the constructors are robust on benchmark data.
            pass
        try:
            nn = nearest_neighbor(instance, rng=rng)
            population.append(giant_tour_from_solution(nn))
        except Exception:  # pragma: no cover - defensive.
            pass
        baseline_tour = [c for route in instance.baseline_routes for c in route]
        if sorted(baseline_tour) == sorted(customer_ids) and baseline_tour:
            population.append(baseline_tour)

        while len(population) < cfg.population_size:
            shuffled = list(customer_ids)
            rng.shuffle(shuffled)
            population.append(shuffled)
        return population[: cfg.population_size]

    def _fitness(self, chromosome: list[int], instance: ProblemInstance) -> float:
        solution = split_giant_tour(chromosome, instance)
        energy = total_energy(solution, instance)
        drone = instance.drone
        if drone.fleet_limited and drone.fleet_size is not None:
            overflow = max(0, solution.num_routes - drone.fleet_size)
            energy += overflow * self.config.fleet_penalty
        return energy

    def _tournament(
        self,
        scored: list[tuple[float, list[int]]],
        rng: random.Random,
    ) -> list[int]:
        size = min(self.config.tournament_size, len(scored))
        contenders = rng.sample(scored, size)
        contenders.sort(key=lambda pair: pair[0])
        return list(contenders[0][1])

    def _maybe_mutate(self, chromosome: list[int], rng: random.Random) -> list[int]:
        if rng.random() >= self.config.mutation_rate:
            return chromosome
        operator = rng.choice(self._mutation_operators)
        return operator(chromosome, rng)
