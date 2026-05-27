# Drone-Based Delivery Optimisation

End-to-end toolkit for the drone-based last-mile delivery routing problem:
a configurable 3D dataset generator, two metaheuristic solvers (Genetic
Algorithm and Simulated Annealing), a command-line interface, a benchmark
runner, and an interactive web cockpit for live exploration.

## What's in the box

| Module | Purpose |
|---|---|
| [data_generator/](data_generator/) | Generates 3D benchmark instances with terrain, no-fly zones, customers and a precomputed asymmetric obstacle-aware travel-cost matrix. |
| [metaheuristics/](metaheuristics/) | Self-contained solver library: domain model, evaluator, repair pipeline, problem-specific operators, GA, SA, and a typed result schema. |
| [scripts/](scripts/) | Command-line utilities — instance generation, dataset visualisation, single-run solver, multi-instance benchmark sweep. |
| [app/](app/) | FastAPI backend that wraps the solver library, streams convergence updates and persists run results. |
| [web/](web/) | Vite + React + TypeScript + Tailwind frontend — the "Cockpit" UI for picking a dataset, launching a solver and inspecting the routes in 3D. |
| [docs/](docs/) | Design documents — data generation, metaheuristic solvers, source assignment, benchmark guidance. |
| [data/instances/](data/instances/) | Ten pre-generated benchmark instances (small / medium / large). |
| [tests/](tests/) | Pytest suite covering the data generator and the solver library. |

## Quick start — command-line

Install the solver dependencies:

```
py -3.13 -m pip install -r requirements.txt
```

Run Simulated Annealing on the smallest benchmark instance:

```
py -3.13 scripts/solve_metaheuristic.py sa data/instances/instance_01_basic_small.json
```

Run the Genetic Algorithm with a fixed seed and save the report:

```
py -3.13 scripts/solve_metaheuristic.py ga data/instances/instance_05_dense_medium.json --seed 42 --out data/solver_runs/ga_inst05.json
```

Sample output:

```
[simulated_annealing] instance_01_basic_small: energy=260.85  routes=2  feasible=True  iterations=29800  runtime=1.03s
  routes:
    drone 1: stops=7   load=20/25  energy=175.22/500.0
      path: depot -> 11 -> 6 -> 10 -> 8 -> 12 -> 1 -> 4 -> depot
    drone 2: stops=5   load=17/25  energy=85.64/500.0
      path: depot -> 9 -> 5 -> 2 -> 3 -> 7 -> depot
```

Pass `--quiet-routes` to suppress the per-drone breakdown. See
`scripts/solve_metaheuristic.py --help` for every available knob
(temperature, cooling rate, population size, etc.).

Run the bulk benchmark sweep across all 10 instances (used for the
comparative study):

```
py -3.13 scripts/benchmark_metaheuristics.py
```

Outputs land under `data/solver_runs/` — one JSON report per `(instance,
algorithm)` pair plus a `summary.csv` for downstream plotting.

## Quick start — web cockpit

The web UI provides an interactive way to pick an instance, tune
hyperparameters, watch the convergence chart update live and inspect the
resulting routes on a 3D terrain map. It is a thin client on top of the
same solver library.

### 1. Start the API

```
py -3.13 -m pip install -r requirements-app.txt
py -3.13 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger docs at <http://localhost:8000/docs>.

### 2. Start the frontend

```
cd web
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` calls
to FastAPI, so both processes must be running.

### Cockpit features

| Feature | Details |
|---|---|
| Dataset picker | Choose one of the 10 benchmark instances |
| Algorithm picker | Toggle between GA and SA, tweak hyperparameters with sliders |
| Live convergence | Server-sent events stream the best-so-far energy and (for SA) the temperature |
| 3D mission map | Terrain surface, no-fly zones as boxes, depot, customers, animated drone routes |
| Per-drone stats | Payload gauge, battery gauge, ordered customer chips, click to isolate on the map |
| Compare view | Side-by-side diff of any two saved runs |
| Run history | Table of past runs, click to re-open |

Keyboard shortcuts: `1`–`9` quick-pick an instance, `/` focus the
dataset dropdown, `R` re-run with the same config, `C` open the Compare
view (when a result is loaded).

## Repository layout

```
data_generator/                  # 3D dataset generation pipeline
metaheuristics/                  # Solver library
├── core/                          # ProblemInstance, Solution, Evaluator, Repair
├── operators/                     # Problem-specific operators
├── algorithms/                    # GA + SA behind a Strategy interface
└── reporting/                     # SolveResult dataclass + JSON serialiser
scripts/                         # CLIs: generate, visualize, solve, benchmark
app/                             # FastAPI backend
├── api/                           # Endpoint routers
├── services/                      # Solver runner + instance cache
├── schemas/                       # Pydantic request/response models
└── tests/                         # API integration tests
web/                             # React + TS + Tailwind frontend
└── src/
    ├── api/                       # Typed API client + SSE helper
    ├── components/                # Run configurator, 3D map, stats panel
    ├── pages/                     # Cockpit, Compare, History
    └── store/                     # Zustand global state
data/
├── instances/                     # 10 benchmark JSON files
└── solver_runs/                   # Saved solver outputs (gitignored)
docs/                            # Design documents
tests/                           # Pytest suite for solver + generator
```

## Documentation

- [docs/metaheuristics.md](docs/metaheuristics.md) — solver design, operator
  catalogue, problem-specific operators, algorithm pseudocode and
  configuration reference.
- [docs/data_generation.md](docs/data_generation.md) — the 3D dataset
  generation pipeline, the obstacle model and the cost matrix.
- [docs/benchmarks.md](docs/benchmarks.md) — benchmark instance catalogue
  and assumptions.
- [docs/source_assignment.md](docs/source_assignment.md) — provenance and
  authorship notes.

## Testing

```
pytest tests/        # solver library and data generator
pytest app/tests/    # API integration tests
cd web && npm test   # frontend store / util tests (if configured)
```

All 31 metaheuristic tests run in under one second alongside the
data-generation suite.

## Data contract

Every solver in this repository — current metaheuristics and the planned
exact method — consumes the same JSON `travel_cost_matrix` embedded in
each instance file. The matrix is asymmetric (vertical climb costs more
than descent) and obstacle-aware (a leg blocked by a no-fly zone is
priced at the ascend-cruise-descend path that goes around it). Sharing
the matrix verbatim is what makes the comparative study fair: every
algorithm optimises against the identical cost model.
