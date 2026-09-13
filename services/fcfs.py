"""FCFS baseline route generation.

This source module replaces the unusable stand-alone ``.pyc`` cache files and
keeps the dictionary contract expected by ``pages/optimization.py``.
"""

from typing import Any

import pandas as pd

from services.routing.distance_matrix import haversine


REQUIRED_COLUMNS = {
    "order_id",
    "customer_id",
    "created_at",
    "latitude",
    "longitude",
    "hub_latitude",
    "hub_longitude",
}


def build_fcfs_route(df: pd.DataFrame) -> dict[str, Any]:
    """Sort orders by creation time and create an open FCFS route.

    The returned route is ``hub -> customer 1 -> ... -> customer N`` and does
    not include the return leg to the hub.
    """
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    if df.empty:
        raise ValueError("FCFS requires at least one order")

    orders = df.copy()
    orders["created_at"] = orders["created_at"].astype(str)
    orders = orders.sort_values("created_at", ascending=True, kind="stable").reset_index(drop=True)

    hub = (
        float(orders.iloc[0]["hub_latitude"]),
        float(orders.iloc[0]["hub_longitude"]),
    )
    customers = [
        (float(row.latitude), float(row.longitude))
        for row in orders.itertuples()
    ]
    points = [hub] + customers

    legs = []
    total_distance_km = 0.0
    for sequence in range(1, len(points)):
        distance_km = haversine(points[sequence - 1], points[sequence])
        total_distance_km += distance_km
        order = orders.iloc[sequence - 1]
        legs.append({
            "sequence": sequence,
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "distance_from_previous_km": round(distance_km, 4),
        })

    return {
        "hub": hub,
        "orders": orders,
        "customers": customers,
        "points": points,
        "legs": legs,
        "total_distance_km": round(total_distance_km, 4),
    }
