"""Step 4: final leg-level output packaging."""

from typing import Mapping, Sequence


def build_leg_distances(
    route: Sequence[int],
    stops: Sequence[Mapping[str, object]],
    distance_matrix: Sequence[Sequence[float]],
) -> list[dict[str, object]]:
    """Package every destination with 0.0001 km (10 cm) precision."""
    legs = []
    for sequence, (previous, current) in enumerate(zip(route, route[1:]), start=1):
        stop = stops[current]
        legs.append({
            "sequence": sequence,
            "order_id": stop.get("order_id"),
            "customer_id": stop.get("customer_id"),
            "distance_from_previous_km": round(float(distance_matrix[previous][current]), 4),
        })
    return legs
