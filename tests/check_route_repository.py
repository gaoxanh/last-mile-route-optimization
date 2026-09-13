from pathlib import Path
import pandas as pd

from database.connection import get_connection
from services.fcfs import build_fcfs_route
from services.two_opt import optimize_2opt
from services.emission import (
    calculate_co2,
    DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
)
from services.route_repository import save_route, get_routes, get_route_stops


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "sample_orders.csv"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cannot find dataset: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    with get_connection() as conn:
        batch = conn.execute(
            """
            SELECT batch_id, vehicle_id
            FROM delivery_batches
            ORDER BY batch_id
            LIMIT 1
            """
        ).fetchone()

    if batch is None:
        raise RuntimeError(
            "No delivery batch found in database. "
            "Load the sample data into the database first."
        )

    batch_id = batch["batch_id"]
    vehicle_id = batch["vehicle_id"]

    fcfs = build_fcfs_route(df)

    fcfs_stops = []
    for leg in fcfs["legs"]:
        fcfs_stops.append({
            "sequence": leg["sequence"],
            "order_id": int(str(leg["order_id"]).replace("O", "")),
            "distance_from_previous_km": leg["distance_from_previous_km"],
        })

    fcfs_co2 = calculate_co2(
        fcfs["total_distance_km"],
        DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
    )

    fcfs_route_id = save_route(
        batch_id=batch_id,
        vehicle_id=vehicle_id,
        route_type="FCFS",
        distance_km=fcfs["total_distance_km"],
        co2_kg=fcfs_co2,
        stops=fcfs_stops,
    )

    customers = [
        (float(row.latitude), float(row.longitude))
        for row in fcfs["orders"].itertuples()
    ]

    optimized = optimize_2opt(fcfs["hub"], customers)

    coord_to_order = {
        (float(row.latitude), float(row.longitude)): int(
            str(row.order_id).replace("O", "")
        )
        for row in df.itertuples()
    }

    optimized_stops = []
    for sequence, point in enumerate(optimized["customers"], start=1):
        previous = (
            fcfs["hub"]
            if sequence == 1
            else optimized["customers"][sequence - 2]
        )

        from services.distance import haversine

        optimized_stops.append({
            "sequence": sequence,
            "order_id": coord_to_order[point],
            "distance_from_previous_km": haversine(
                previous[0], previous[1], point[0], point[1]
            ),
        })

    optimized_co2 = calculate_co2(
        optimized["optimized_distance_km"],
        DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
    )

    optimized_route_id = save_route(
        batch_id=batch_id,
        vehicle_id=vehicle_id,
        route_type="OPTIMIZED",
        distance_km=optimized["optimized_distance_km"],
        co2_kg=optimized_co2,
        stops=optimized_stops,
    )

    print("=" * 65)
    print("DATABASE ROUTE SAVE CHECK")
    print("=" * 65)
    print(f"Batch ID: {batch_id}")
    print(f"Vehicle ID: {vehicle_id}")
    print(f"FCFS route saved     : {fcfs_route_id}")
    print(f"OPTIMIZED route saved: {optimized_route_id}")

    print("\nSaved routes:")
    for route in get_routes(batch_id):
        print(
            f"{route['route_id']} | "
            f"{route['route_type']} | "
            f"{route['distance_km']:.2f} km | "
            f"{route['co2_kg']:.2f} kg CO2"
        )

    print("\nFCFS stops:")
    for stop in get_route_stops(fcfs_route_id):
        print(
            f"{stop['sequence']:02d}. "
            f"O{stop['order_id']:03d} | "
            f"{stop['distance_from_previous']:.2f} km"
        )

    print("=" * 65)


if __name__ == "__main__":
    main()
