"""FCFS baseline route generation.

FCFS is responsible only for defining the chronological baseline order.
Distance, duration and emissions are calculated by the central routing
orchestrator using the same OSRM road-network model as the optimised route.
"""

from typing import Any

import pandas as pd


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
    """Sort orders by creation time and return the FCFS baseline data.

    The route sequence itself is chronological. The central orchestrator is
    responsible for adding the return-to-hub leg and calculating road-network
    distance/duration.
    """
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    if df.empty:
        raise ValueError("FCFS requires at least one order")

    orders = df.copy()
    orders["created_at"] = orders["created_at"].astype(str)
    orders = orders.sort_values(
        "created_at",
        ascending=True,
        kind="stable",
    ).reset_index(drop=True)

    hub = (
        float(orders.iloc[0]["hub_latitude"]),
        float(orders.iloc[0]["hub_longitude"]),
    )
    customers = [
        (float(row.latitude), float(row.longitude))
        for row in orders.itertuples()
    ]

    return {
        "hub": hub,
        "orders": orders,
        "customers": customers,
        "points": [hub] + customers,
    }
