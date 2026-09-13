"""Step 3: bottleneck penalties and optimisation of unvisited stops."""

from dataclasses import dataclass
from typing import Sequence

from .two_opt import two_opt

Matrix = Sequence[Sequence[float]]


@dataclass(frozen=True)
class Bottleneck:
    from_index: int
    to_index: int
    distance_multiplier: float = float("inf")
    duration_multiplier: float = float("inf")
    bidirectional: bool = False
    reason: str = "traffic disruption"


def _penalize(matrix: Matrix, disruptions: Sequence[Bottleneck], attribute: str) -> list[list[float]]:
    result = [list(row) for row in matrix]
    for item in disruptions:
        multiplier = getattr(item, attribute)
        result[item.from_index][item.to_index] *= multiplier
        if item.bidirectional:
            result[item.to_index][item.from_index] *= multiplier
    return result


def apply_penalties(
    distance_matrix: Matrix,
    duration_matrix: Matrix,
    disruptions: Sequence[Bottleneck],
) -> tuple[list[list[float]], list[list[float]]]:
    """Copy matrices and penalise only the affected directed road segments."""
    return (_penalize(distance_matrix, disruptions, "distance_multiplier"),
            _penalize(duration_matrix, disruptions, "duration_multiplier"))


def reroute_remaining(
    current_route: Sequence[int],
    completed_leg_count: int,
    penalized_distance_matrix: Matrix,
) -> list[int]:
    """Preserve travelled legs and run 2-opt only from the current stop onward."""
    if not 0 <= completed_leg_count < len(current_route):
        raise ValueError("completed_leg_count is outside the route")
    prefix = list(current_route[:completed_leg_count])
    remaining = list(current_route[completed_leg_count:])
    optimized_remaining = two_opt(remaining, penalized_distance_matrix, fix_start=True, fix_end=True)
    return prefix + optimized_remaining
