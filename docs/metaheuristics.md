# Metaheuristic solvers — design document

This document covers the design, architecture and operator catalogue of the
two metaheuristic solvers shipped in this project:

- **Population-based search** — a Genetic Algorithm operating on a
  giant-tour permutation encoding with Prins' optimal split decoder.
- **Local search** — Simulated Annealing operating on a list-of-routes
  encoding with a five-move neighbourhood.

Both solvers share a common substrate of **problem-specific operators**
(encoding, construction, neighbourhood exploration, crossover, mutation
and feasibility-preserving repair) that are tailored to the drone routing
constraints — payload, battery, fleet size and asymmetric obstacle-aware
travel costs.

The implementation lives under [metaheuristics/](../metaheuristics/) and is
exercised by the suite under [tests/](../tests/) and the CLI in
[scripts/solve_metaheuristic.py](../scripts/solve_metaheuristic.py).

## 1. Problem recap

Given a depot (node `0`), `N` customers with positive integer demands, a
homogeneous fleet of drones with a payload limit `Q` and a battery budget
`B`, and an optional fleet-size limit `K`, design routes that:

1. start and end at the depot,
2. visit each customer exactly once,
3. respect `Q` (sum of demands on a route) and `B` (route energy),
4. respect `K` when set,

while minimising the **total energy** spent across all routes. Energy along
an edge is read from the precomputed asymmetric `travel_cost_matrix` that
the data generator embeds in every benchmark file. Using that matrix
verbatim means the metaheuristics share the *exact same* cost model as the
exact (Branch-and-Bound) baseline planned for Task 3.

## 2. Package architecture

```
metaheuristics/
├── core/         # Domain layer: ProblemInstance, Solution, Evaluator, Repair
├── operators/    # Problem-specific operators: encoding, construction,
│                 #   neighbourhood, crossover, mutation
├── algorithms/   # Strategy interface + GeneticAlgorithm + SimulatedAnnealing
└── reporting/    # SolveResult dataclass + JSON serialiser
```

The package follows a clean **layered** architecture:

- **Core** owns the immutable problem model and the objective function. It
  never depends on any other layer.
- **Operators** transform candidate solutions. They depend only on Core.
- **Algorithms** orchestrate operators behind a tiny **Strategy** interface
  (`Metaheuristic.solve(instance) -> SolveResult`). The CLI and the
  benchmark runner consume that interface, so they treat solvers
  interchangeably.
- **Reporting** owns the result schema. It is intentionally separated from
  the solvers so that downstream tooling (comparative analysis, plots,
  dashboards) can read run reports without re-running the solvers.

### Why two encodings?

- **List-of-routes** (canonical) is the natural representation for the
  neighbourhood operators of the SA. It makes feasibility checks and
  repair operators straightforward (you can inspect a single route in
  isolation).
- **Giant tour** (a permutation of customer IDs) is the natural
  representation for the GA. Recombination and mutation become trivial
  permutation operators, and the decoder
  ([`split_giant_tour`](../metaheuristics/operators/encoding.py)) computes
  the **optimal feasible partition** of the permutation in `O(N²)` via a
  Bellman-style DP (Prins, 2004).

Both forms talk to the same `ProblemInstance` and produce the same
`Solution`. The encoding module is the bridge.

## 3. Core layer

### `ProblemInstance` (`metaheuristics/core/instance.py`)

Immutable, fully typed view of a benchmark JSON file. Exposes:

- `depot`, `customers` (typed `Node` records),
- `drone` (`DroneProfile` with `payload_capacity`, `battery_capacity`,
  optional `fleet_size`),
- `cost_matrix` and `distance_matrix` as tuples of tuples for O(1)
  integer indexing,
- `cost(i, j)` / `distance(i, j)` helpers,
- `baseline_routes` (the certificate emitted by the generator — used as a
  seed in the GA population).

### `Solution`, `Route` (`metaheuristics/core/solution.py`)

The list-of-routes container. Provides `to_depot_zero_array()` and
`from_depot_zero_array()` so we can read/write the exact array form named
in the project statement (`[0, c, c, 0, c, ..., 0]`).

### Evaluator (`metaheuristics/core/evaluator.py`)

Pure functions:

- `evaluate_route(customers, instance)` — energy of one closed route.
- `total_energy(solution, instance)` — objective value.
- `is_feasible(solution, instance)` — short-circuit boolean check.
- `evaluate_solution(solution, instance) -> Evaluation` — full report with
  human-readable violations (used by the CLI and tests).

### Repair (`metaheuristics/core/repair.py`)

`repair_solution(...)` walks every route, splits the customer order at
the first capacity or battery overflow, then merges tail routes greedily
to fit `K` when the fleet is limited. The split preserves customer order
so neighbourhood / mutation semantics survive the repair.

## 4. Problem-specific operators

A metaheuristic is only as good as the operators it manipulates. Generic
permutation operators (uniform random swap, single-point crossover…) treat
a candidate solution as an abstract list of integers — they have no idea
that the integers represent drone stops constrained by payload, battery,
no-fly zones and a fleet bound. Applied blindly, such operators spend most
of their budget producing infeasible candidates that the solver then has to
reject.

A **problem-specific operator** is one that bakes the structure of the
drone routing problem into the move itself: it knows what a route is, what
the depot is, how payload and battery interact, and how to keep a solution
feasible (or how to restore feasibility cheaply when a move breaks it). The
project rubric breaks these operators into four categories — *encoding*,
*construction*, *neighbourhood* and *repair* — and this section walks
through how each is realised in the codebase.

### 4.1 Encoding — how a solution is stored

The encoding decides what the solvers are allowed to think about. Two
complementary forms coexist:

**List-of-routes (canonical form).** A `Solution` is a list of `Route`
objects, each a list of customer IDs. The depot is implicit at both ends.
This is the natural form for the SA: every neighbourhood move modifies a
specific route or a pair of routes, so having the route boundaries
explicit makes the moves and the repair operator easy to write and to
test.

**Giant tour (permutation form).** A single list `[c1, c2, …, cN]`
containing every customer ID exactly once, with no depot markers. This is
the natural form for the GA: classical permutation operators (order
crossover, swap mutation, inversion) become trivial because there are no
route boundaries to preserve. The boundaries are *recovered* at
evaluation time by the **Split decoder** `split_giant_tour(tour,
instance)` — a Bellman-style DP that, given the tour order, computes the
**optimal feasible partition** into routes in `O(N²)` time and `O(N)`
space (Prins, 2004). Split honours payload and battery exactly, so every
chromosome decodes into a guaranteed-feasible solution without a separate
repair pass.

**Flat depot-zero array.** `Solution.to_depot_zero_array()` and
`Solution.from_depot_zero_array()` round-trip between the canonical form
and the array `[0, c, c, …, 0, c, …, 0]` that the project statement names
as the textbook representation. The codebase uses it for I/O and
debugging but not as the primary working form.

### 4.2 Construction — how an initial solution is built

The metaheuristics need a starting point. A blank or fully random start
wastes early iterations on basic feasibility; a good seed lets the search
spend its budget on actual improvement. Three constructors are available:

| Operator | Determinism | Used by | What it does |
|---|---|---|---|
| `nearest_neighbor` | Greedy with RNG tie-break | SA warm start | Extends the active route to the nearest customer that still leaves enough battery to return home and payload to fit the demand; otherwise closes the route and starts a new one. |
| `clarke_wright_savings` | Deterministic | GA seed (one chromosome) and SA option | Adapts Clarke & Wright's savings heuristic to the **asymmetric** cost matrix by enumerating both orderings of each pair `(i, j)`. Merges customer pairs by descending savings while respecting payload and battery on the combined route. |
| `random_split` | Stochastic | GA initial population | Generates a uniformly random permutation and decodes it through Split. Provides population diversity without violating any constraint. |

Every constructor produces a *feasible* solution — no post-construction
repair pass is needed.

### 4.3 Neighbourhood — what a "small change" looks like

A neighbourhood operator defines the local search topology. The SA picks
one of these five moves uniformly at random per inner iteration:

| Move | Structural change | Routes touched |
|---|---|---|
| `swap_move` | Exchange two customers (intra- or inter-route) | 1 or 2 |
| `relocate_move` | Remove a customer, reinsert it at a different position | 1 or 2 |
| `or_opt_move` | Move a chain of 2–3 consecutive customers to a new position | 1 or 2 |
| `two_opt_move` | Reverse a sub-segment of a single route (uncrosses self-intersections) | 1 |
| `two_opt_star_move` | Exchange the tails of two routes after a cut point in each | 2 |

What makes these "drone-specific" rather than generic combinatorial
operators:

- They operate at the route level, not at the giant-tour level, so they
  preserve the multi-route structure the SA is searching.
- They route every result through `repair_solution` before returning, so
  even when a move temporarily breaks payload or battery, the caller
  receives a feasible neighbour or `None`. The SA never has to validate;
  it only compares energies.
- Their cost is read from the same asymmetric cost matrix the solver uses
  for the objective — there is no separate distance model to keep in
  sync.

The `NEIGHBORHOOD_MOVES` registry exposes these as a uniform set the SA
samples from.

### 4.4 Crossover and mutation — how the population evolves

These are the GA-side counterparts of the neighbourhood operators.

**Crossover.** `order_crossover` (OX1) takes two parent permutations and
two cut points `i < j`. The slice `parent_a[i:j]` is copied into the
offspring at the same positions; the remaining positions are filled by
walking `parent_b` cyclically from index `j`, skipping any customer
already placed. The result is always a valid permutation — by
construction every customer appears exactly once. Combined with Split at
decoding time, OX1 inherits route boundaries from both parents while
keeping the recombined solution feasible.

**Mutation.** Three operators are applied with probability
`mutation_rate`:

- `swap_mutation` — swap two random positions in the giant tour.
- `inversion_mutation` — reverse a random sub-segment. This is the
  giant-tour analogue of 2-opt; combined with Split it is very effective
  because route boundaries are re-optimised at every decoding, so an
  inversion can implicitly reshape the route partition.
- `relocate_mutation` — extract one position and reinsert it elsewhere.

All three preserve the permutation invariant by construction.

### 4.5 Repair — how feasibility is restored

The repair operator is the central feasibility gate. It is the explicit
example given in the project statement:

> *If a mutation causes a drone to exceed its battery limit, the repair
> operator forcibly splits the route and inserts a return trip to the
> depot to swap the battery.*

The implementation in [metaheuristics/core/repair.py](../metaheuristics/core/repair.py)
follows that recipe exactly. `repair_solution(solution, instance)` works
in three stages:

1. **Drop empty routes.** Any route with no customers is removed.
2. **Split overlong routes.** `split_overlong_route(customers, instance)`
   walks the customer list in order. It maintains a running prefix that
   is still feasible (payload and closed-loop battery). The instant
   adding the next customer would push the prefix over either limit, it
   closes the current route there — sending the drone home — and starts
   a fresh route with that customer. The split is
   **order-preserving**, so structural information injected by a
   mutation or a neighbourhood move (e.g. a freshly improved sub-segment)
   survives the repair.
3. **Merge to fit fleet size.** When the instance caps the fleet at `K`
   routes, a greedy merge pass tries to combine route pairs whose union
   is still feasible. If no merge can satisfy `K`, the surplus routes
   remain and the caller penalises the fitness — this avoids destroying
   diversity by killing borderline-infeasible candidates outright.

Two important properties of this repair pipeline:

- **It is closed-loop aware.** Battery feasibility is measured against
  the full `depot → … → depot` round-trip, so a route is never accepted
  if the drone could reach its last customer but not return home. This
  is the architectural answer to the "what if the drone runs out of fuel
  after the last delivery" question.
- **It is the single feasibility authority.** Every neighbourhood move
  and every mutation calls `repair_solution` before returning, so the
  rest of the codebase can treat *being in the operator output set* as
  equivalent to *being feasible*. The SA and GA never need to re-check
  payload or battery — they only compare energies.

## 5. Algorithms

### 5.1 Simulated Annealing

```
T <- T_0
solution <- nearest_neighbor(instance)
best <- solution
while T > T_min and not budget exhausted:
    repeat inner_iterations times:
        move <- pick uniform random move
        candidate <- move(solution)
        Δ <- E(candidate) - E(solution)
        if Δ < 0 or U(0,1) < exp(-Δ / T):
            solution <- candidate
            best <- candidate if E(candidate) < E(best)
    T <- α * T
```

Configurable knobs (`SAConfig`):

- `initial_temperature` (default 100), `min_temperature` (0.05),
  `cooling_rate` (0.95, geometric schedule),
- `inner_iterations` (200), `max_iterations` (50,000),
- `no_improvement_window` for early stop,
- `construction` to swap between nearest-neighbour and savings warm start,
- `record_history` for the convergence trace.

### 5.2 Genetic Algorithm

Generational GA with elitism. Each chromosome is a permutation of customer
IDs; fitness is the total energy returned by Split, plus a soft penalty
when a fleet limit is exceeded.

```
population <- {savings tour, NN tour, baseline tour, random tours...}
evaluate(population)
for g = 1 .. generations:
    elites <- top-`elitism` chromosomes
    while |next| < population_size:
        a, b <- tournament(scored)
        if rand() < crossover_rate: (a, b) <- OX1(a, b)
        a <- maybe_mutate(a); b <- maybe_mutate(b)
        next.append(a, b)
    population <- next
    evaluate(population)
```

Configurable knobs (`GAConfig`): `population_size`, `generations`,
`tournament_size`, `crossover_rate`, `mutation_rate`, `elitism`,
`no_improvement_generations`, `fleet_penalty`, `random_seed`,
`record_history`.

## 6. Running the solvers

Single-run CLI:

```
python scripts/solve_metaheuristic.py sa data/instances/instance_01_basic_small.json
python scripts/solve_metaheuristic.py ga data/instances/instance_05_dense_medium.json --seed 42 --out runs/ga_inst05.json
```

The CLI prints the per-drone route, payload usage and battery usage after
each run; pass `--quiet-routes` to suppress that section.

Bulk benchmark sweep for the comparative study:

```
python scripts/benchmark_metaheuristics.py
```

The benchmark runner writes a per-instance JSON report and a `summary.csv`
under `data/solver_runs/`.

Interactive web UI:

```
py -3.13 -m uvicorn app.main:app --reload --port 8000
cd web && npm run dev
```

The cockpit is then available at `http://localhost:5173` with the API at
`http://localhost:8000`. See the top-level [README](../README.md) for a
full setup walkthrough.

## 7. Reference results

A first sanity run on three representative instances (defaults, single seed)
already beats the baseline certificate by a large margin:

| Instance | Customers | Fleet | Baseline | SA | GA |
|---|---:|---:|---:|---:|---:|
| `instance_01_basic_small` | 12 | unlimited | 385.76 | **267.16** | **261.57** |
| `instance_02_basic_medium` | 30 | unlimited | 1522.18 | **978.56** | **1016.53** |
| `instance_07_dense_large_tight` | 120 | 24 | 10829.19 | **6903.30** | **5708.33** |
| `instance_10_max_extreme` | 150 | 30 | 16543.28 | **9694.45** | **7879.83** |

Both solvers reach feasible solutions and the GA tends to scale better on
the larger fleet-limited instances thanks to Split's optimal partitioning.

## 8. Testing strategy

- **Unit tests** for every layer:
  [tests/test_metaheuristics_core.py](../tests/test_metaheuristics_core.py)
  exercises the loader, the evaluator and the repair pipeline against a
  real instance.
- **Operator tests** in
  [tests/test_metaheuristics_operators.py](../tests/test_metaheuristics_operators.py)
  assert that each construction and each neighbourhood move produces a
  feasible solution (or `None`), and that crossover/mutation preserve the
  permutation invariant.
- **End-to-end tests** in
  [tests/test_metaheuristics_algorithms.py](../tests/test_metaheuristics_algorithms.py)
  run the SA and GA with small budgets and verify that they (a) return
  feasible solutions and (b) improve on the deterministic nearest-neighbour
  warm start.

All 31 metaheuristic tests run in under one second alongside the existing
data-generation tests (`pytest`).
