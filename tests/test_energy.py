from __future__ import annotations

from dataclasses import dataclass

from data_generator.energy import straight_line_energy
from data_generator.models import EnergyCosts


@dataclass(frozen=True)
class Point:
    x: int
    y: int
    z: int


def test_ascent_and_descent_can_be_asymmetric() -> None:
    costs = EnergyCosts(
        horizontal_rate=1.0,
        vertical_ascend_multiplier=2.0,
        vertical_descend_multiplier=0.5,
        hover_rate=0.0,
    )
    low = Point(0, 0, 0)
    high = Point(0, 0, 10)
    assert straight_line_energy(low, high, costs) == 20.0
    assert straight_line_energy(high, low, costs) == 5.0
