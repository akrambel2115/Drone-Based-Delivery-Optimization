"""Solution value objects.

The canonical representation of a candidate solution is the
**list-of-routes** form: ``solution.routes = [[c1, c2, ...], [c3, ...], ...]``
where each inner list is the ordered sequence of customer IDs visited
between two depot stops.

The depot does **not** appear in the route lists; it is implicit at both
ends. This keeps neighborhood operators concise and avoids the bookkeeping
errors that come with treating ``0`` like a regular node.

The :class:`Solution` is intentionally a mutable container so that
metaheuristic operators can rearrange its routes in place. When immutability
is required (for archives, best-so-far snapshots, etc.), call
:meth:`Solution.clone` to obtain an independent copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Sequence


@dataclass
class Route:
    """An ordered sequence of customer IDs visited by a single drone."""

    customers: list[int] = field(default_factory=list)

    def __iter__(self) -> Iterator[int]:
        return iter(self.customers)

    def __len__(self) -> int:
        return len(self.customers)

    def __bool__(self) -> bool:
        return bool(self.customers)

    def clone(self) -> "Route":
        return Route(list(self.customers))


@dataclass
class Solution:
    """A complete partition of customers into feasible drone routes.

    Routes are ordered, but the ordering is arbitrary: it does not affect
    feasibility or cost. Empty routes are dropped during normalisation.
    """

    routes: list[Route] = field(default_factory=list)

    # --- constructors ----------------------------------------------------

    @classmethod
    def from_lists(cls, route_lists: Iterable[Sequence[int]]) -> "Solution":
        return cls(routes=[Route(list(r)) for r in route_lists if r])

    # --- iteration / introspection --------------------------------------

    def __iter__(self) -> Iterator[Route]:
        return iter(self.routes)

    def __len__(self) -> int:
        return len(self.routes)

    @property
    def num_routes(self) -> int:
        return len(self.routes)

    def all_customers(self) -> list[int]:
        """Flat list of every customer visited (in route order)."""
        return [customer for route in self.routes for customer in route.customers]

    # --- mutation helpers ----------------------------------------------

    def clone(self) -> "Solution":
        return Solution(routes=[route.clone() for route in self.routes])

    def drop_empty_routes(self) -> None:
        """Remove zero-length routes in place."""
        self.routes = [route for route in self.routes if route.customers]

    # --- serialisation --------------------------------------------------

    def to_depot_zero_array(self) -> list[int]:
        """Flatten to the ``[0, c, c, 0, c, ..., 0]`` array required by the spec.

        Example
        -------
        ``Solution([[1, 2], [3]]).to_depot_zero_array() == [0, 1, 2, 0, 3, 0]``.
        """
        out: list[int] = [0]
        for route in self.routes:
            out.extend(route.customers)
            out.append(0)
        return out

    @classmethod
    def from_depot_zero_array(cls, array: Sequence[int]) -> "Solution":
        """Inverse of :meth:`to_depot_zero_array`.

        Trailing/leading depot markers and consecutive zeros are tolerated.
        """
        routes: list[Route] = []
        current: list[int] = []
        for node in array:
            if node == 0:
                if current:
                    routes.append(Route(current))
                    current = []
            else:
                current.append(int(node))
        if current:
            routes.append(Route(current))
        return cls(routes=routes)
