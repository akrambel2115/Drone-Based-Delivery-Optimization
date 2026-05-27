"""Problem-specific operators (Task 5).

The package is organised by *role*, not by algorithm, so the same operators
can be plugged into the GA, the SA, or any future metaheuristic.

Modules
-------
encoding
    Convert between the canonical list-of-routes representation
    (:class:`metaheuristics.core.solution.Solution`) and the "giant tour"
    permutation used by the GA, including Prins' optimal-split decoder.
construction
    Greedy / heuristic initial-solution generators (nearest neighbour,
    Clarke-Wright savings, random + split).
neighborhood
    Local-search moves: swap, relocate (or-opt-1), 2-opt (intra-route),
    or-opt (chain), 2-opt* (inter-route tail exchange).
crossover
    Recombination operators for the GA (currently ordered crossover OX).
mutation
    Mutation operators for the GA (swap, inversion, relocate).
"""

from metaheuristics.operators.construction import (
    clarke_wright_savings,
    nearest_neighbor,
    random_split,
)
from metaheuristics.operators.crossover import order_crossover
from metaheuristics.operators.encoding import (
    giant_tour_from_solution,
    solution_from_giant_tour,
    split_giant_tour,
)
from metaheuristics.operators.mutation import (
    inversion_mutation,
    relocate_mutation,
    swap_mutation,
)
from metaheuristics.operators.neighborhood import (
    NEIGHBORHOOD_MOVES,
    NeighborhoodMove,
    or_opt_move,
    relocate_move,
    swap_move,
    two_opt_move,
    two_opt_star_move,
)

__all__ = [
    "NEIGHBORHOOD_MOVES",
    "NeighborhoodMove",
    "clarke_wright_savings",
    "giant_tour_from_solution",
    "inversion_mutation",
    "nearest_neighbor",
    "or_opt_move",
    "order_crossover",
    "random_split",
    "relocate_move",
    "relocate_mutation",
    "solution_from_giant_tour",
    "split_giant_tour",
    "swap_move",
    "swap_mutation",
    "two_opt_move",
    "two_opt_star_move",
]
