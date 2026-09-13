from pathlib import Path
import pandas as pd

from services.distance import haversine, total_route_distance


# Project root: D:\last-mile-co2
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "sample_orders.csv"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find sample dataset: {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH)

    required_columns = {
        "order_id",
        "customer_id",
        "latitude",
        "longitude",
        "hub_latitude",
        "hub_longitude",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    hub = (
        float(df.iloc[0]["hub_latitude"]),
        float(df.iloc[0]["hub_longitude"]),
    )

    customer_points = [
        (
            float(row.latitude),
            float(row.longitude),
        )
        for row in df.itertuples()
    ]

    print("=" * 60)
    print("DISTANCE CALCULATION CHECK")
    print("=" * 60)
    print(f"Orders: {len(df)}")
    print(
        f"Hub: ({hub[0]:.6f}, {hub[1]:.6f})"
    )

    print("\nHub -> Customer distances:")
    print("-" * 60)

    distances = []

    for row, point in zip(df.itertuples(), customer_points):
        distance = haversine(
            hub[0],
            hub[1],
            point[0],
            point[1],
        )
        distances.append(distance)

        print(
            f"{row.order_id} | {row.customer_id} | "
            f"{distance:7.2f} km"
        )

    # Open FCFS-style distance for the current CSV order.
    # FCFS ordering itself is implemented in Step 4.
    route_points = [hub] + customer_points
    total_distance = total_route_distance(route_points)

    print("\n" + "=" * 60)
    print("DISTANCE SUMMARY")
    print("=" * 60)
    print(f"Nearest customer : {min(distances):.2f} km")
    print(f"Farthest customer: {max(distances):.2f} km")
    print(
        f"Current CSV order distance: "
        f"{total_distance:.2f} km"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
