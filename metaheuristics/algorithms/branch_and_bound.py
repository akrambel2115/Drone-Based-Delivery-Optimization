"""Exact Method (Branch and Bound) using PuLP for the Two-Commodity Network Flow LP relaxation."""

from __future__ import annotations

import dataclasses
import time
from typing import Any, Callable

import pulp

from metaheuristics.algorithms.base import Metaheuristic, SolveResult
from metaheuristics.core.evaluator import evaluate_solution
from metaheuristics.core.instance import ProblemInstance
from metaheuristics.core.solution import Route, Solution
from metaheuristics.operators.construction import nearest_neighbor
from metaheuristics.reporting.result import HistoryEntry


@dataclasses.dataclass
class BBConfig:
    greedy_initialization: bool = True
    record_history: bool = True


class BranchAndBound(Metaheuristic):
    """Exact method using a Branch and Bound tree search.
    
    The lower bound is computed at each node via a Two-Commodity Network Flow 
    LP relaxation of the multi-drone routing problem.
    """

    def __init__(self, config: BBConfig):
        self.config = config
        self.name = "bb"

    def solve(self, instance: ProblemInstance) -> SolveResult:
        return self.solve_streaming(instance, lambda *args: None)

    def solve_streaming(
        self,
        instance: ProblemInstance,
        callback: Callable[[int, float, float | None], None],
    ) -> SolveResult:
        start_time = time.perf_counter()
        
        # 1. Initialization
        best_solution: Solution | None = None
        best_energy = float('inf')
        
        if self.config.greedy_initialization:
            import random
            rng = random.Random(42)
            greedy_sol = nearest_neighbor(instance, rng=rng)
            greedy_eval = evaluate_solution(greedy_sol, instance)
            if greedy_eval.feasible:
                best_solution = greedy_sol
                best_energy = greedy_eval.energy
        
        callback(0, best_energy if best_solution else 0.0, None)
        
        nodes_explored = 0
        history: list[HistoryEntry] = []
        
        # Stack for DFS: each element is (fixed_zeros, fixed_ones)
        # We store them as sets for fast lookup
        stack: list[tuple[set[tuple[int, int]], set[tuple[int, int]]]] = [
            (set(), set())
        ]
        
        N = instance.num_customers
        V = list(range(N + 1))
        
        # Pre-create the static parts of the LP problem to avoid rebuilding if possible?
        # Rebuilding PuLP model in python every time might be slow, but it's the simplest way.
        
        while stack:
            fixed_zeros, fixed_ones = stack.pop()
            nodes_explored += 1
            
            # LP Oracle
            lp_prob = pulp.LpProblem("Drone_Relaxation", pulp.LpMinimize)
            
            # Variables
            # x[i,j] in [0, 1]
            x = pulp.LpVariable.dicts("x", ((i, j) for i in V for j in V if i != j), lowBound=0, upBound=1, cat="Continuous")
            # F[i,j] >= 0
            F = pulp.LpVariable.dicts("F", ((i, j) for i in V for j in V if i != j), lowBound=0, cat="Continuous")
            # Q[i,j] >= 0
            Q = pulp.LpVariable.dicts("Q", ((i, j) for i in V for j in V if i != j), lowBound=0, cat="Continuous")
            
            # Objective
            lp_prob += pulp.lpSum(instance.cost(i, j) * x[i, j] for i in V for j in V if i != j)
            
            # Constraints
            
            # Fleet limit (if any)
            if instance.drone.fleet_limited:
                lp_prob += pulp.lpSum(x[0, j] for j in V if j != 0) <= instance.drone.fleet_size
            
            # Degree constraints for customers
            for i in range(1, N + 1):
                lp_prob += pulp.lpSum(x[i, j] for j in V if i != j) == 1
                lp_prob += pulp.lpSum(x[j, i] for j in V if i != j) == 1
                
            # Depot flow balance
            lp_prob += pulp.lpSum(x[0, j] for j in V if j != 0) == pulp.lpSum(x[j, 0] for j in V if j != 0)

            payload_cap = instance.drone.payload_capacity
            battery_cap = instance.drone.battery_capacity
            
            for i in V:
                for j in V:
                    if i != j:
                        # Flow bounds
                        lp_prob += F[i, j] <= payload_cap * x[i, j]
                        lp_prob += Q[i, j] <= battery_cap * x[i, j]
                        lp_prob += Q[i, j] >= instance.cost(i, j) * x[i, j]
            
            for i in range(1, N + 1):
                # Payload balance
                lp_prob += pulp.lpSum(F[j, i] for j in V if j != i) - pulp.lpSum(F[i, j] for j in V if j != i) == instance.demand_by_id[i]
                # Energy balance
                lp_prob += pulp.lpSum(Q[j, i] for j in V if j != i) - pulp.lpSum(Q[i, j] for j in V if j != i) == pulp.lpSum(instance.cost(j, i) * x[j, i] for j in V if j != i)

            # Apply fixed bounds
            for (i, j) in fixed_zeros:
                lp_prob += x[i, j] == 0
            for (i, j) in fixed_ones:
                lp_prob += x[i, j] == 1
                
            # Solve LP
            # Disable PuLP logging
            solver = pulp.PULP_CBC_CMD(msg=False)
            lp_prob.solve(solver)
            
            status = lp_prob.status
            if status != pulp.LpStatusOptimal:
                continue # Infeasible or unbounded, prune
                
            lb = pulp.value(lp_prob.objective)
            
            if lb >= best_energy:
                continue # Bound pruning
                
            # Integrality check
            fractional_vars = []
            for i in V:
                for j in V:
                    if i != j:
                        val = x[i, j].varValue
                        if val is not None and 1e-5 < val < 1 - 1e-5:
                            # Distance to 0.5
                            fractional_vars.append((abs(val - 0.5), val, i, j))
                            
            if not fractional_vars:
                # Integer solution found!
                # Reconstruct routes
                routes = []
                # Find all outgoing edges from depot
                for j in range(1, N + 1):
                    if x[0, j].varValue is not None and x[0, j].varValue > 0.5:
                        route_nodes = []
                        curr = j
                        while curr != 0:
                            route_nodes.append(curr)
                            # find next
                            for nxt in V:
                                if curr != nxt and x[curr, nxt].varValue is not None and x[curr, nxt].varValue > 0.5:
                                    curr = nxt
                                    break
                        routes.append(Route(customers=tuple(route_nodes)))
                        
                candidate_sol = Solution(routes=tuple(routes))
                candidate_eval = evaluate_solution(candidate_sol, instance)
                if candidate_eval.feasible and candidate_eval.energy < best_energy:
                    best_energy = candidate_eval.energy
                    best_solution = candidate_sol
                    callback(nodes_explored, best_energy, None)
                    if self.config.record_history:
                        history.append(HistoryEntry(
                            iteration=nodes_explored,
                            best_energy=best_energy,
                            current_energy=lb,
                            accepted=True,
                            temperature=None
                        ))
                continue
                
            # Branching (Fractional variable closest to 0.5)
            fractional_vars.sort() # Sorts by distance to 0.5
            _, val, branch_i, branch_j = fractional_vars[0]
            
            # DFS order: explore the branch that seems more promising first.
            # If val is > 0.5, exploring x=1 first might be better, so push x=0 to stack first.
            
            left_zeros = set(fixed_zeros)
            left_zeros.add((branch_i, branch_j))
            right_ones = set(fixed_ones)
            right_ones.add((branch_i, branch_j))
            
            if val > 0.5:
                stack.append((left_zeros, fixed_ones))
                stack.append((fixed_zeros, right_ones))
            else:
                stack.append((fixed_zeros, right_ones))
                stack.append((left_zeros, fixed_ones))

            if nodes_explored % 10 == 0:
                callback(nodes_explored, best_energy, None)

        runtime = time.perf_counter() - start_time
        
        evaluation = None
        if best_solution:
            evaluation = evaluate_solution(best_solution, instance)
            
        return SolveResult(
            algorithm=self.name,
            instance_name=instance.name,
            best_solution=best_solution if best_solution else Solution(routes=()),
            best_evaluation=evaluation if evaluation else evaluate_solution(Solution(routes=()), instance),
            history=history,
            iterations=nodes_explored,
            runtime_seconds=runtime,
            config=dataclasses.asdict(self.config),
            notes={"lp_nodes": nodes_explored}
        )

