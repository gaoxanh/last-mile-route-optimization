"""Step 2: matrix-driven 2-opt route optimisation."""

import math
from typing import Sequence

Matrix = Sequence[Sequence[float]]


def route_cost(route: Sequence[int], matrix: Matrix) -> float:
    return sum(matrix[a][b] for a, b in zip(route, route[1:]))


def two_opt(
    route: Sequence[int],
    matrix: Matrix,
    *,
    fix_start: bool = True,
    fix_end: bool = True,
    max_passes: int = 100,
) -> list[int]:
    """Improve a route by repeatedly reversing a contiguous subsequence."""
    best = list(route)
    if len(best) < 4:
        return best
    best_cost = route_cost(best, matrix)
    left = 1 if fix_start else 0
    right = len(best) - 1 if fix_end else len(best)
    for _ in range(max_passes):
        improved = False
        for i in range(left, right - 1):
            for k in range(i + 1, right):
                candidate = best[:i] + list(reversed(best[i:k + 1])) + best[k + 1:]
                candidate_cost = route_cost(candidate, matrix)
                if candidate_cost + 1e-12 < best_cost:
                    best, best_cost, improved = candidate, candidate_cost, True
        if not improved:
            break
    if math.isinf(best_cost):
        raise ValueError("no finite route is available with the current penalties")
    return best
