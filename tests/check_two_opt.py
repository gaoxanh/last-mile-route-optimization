from pathlib import Path
import pandas as pd

from services.fcfs import build_fcfs_route
from services.two_opt import optimize_2opt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "sample_orders.csv"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cannot find dataset: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    fcfs = build_fcfs_route(df)

    customers = [
        (float(row.latitude), float(row.longitude))
        for row in fcfs["orders"].itertuples()
    ]

    result = optimize_2opt(fcfs["hub"], customers)

    baseline = result["baseline_distance_km"]
    optimized = result["optimized_distance_km"]
    reduction = (
        (baseline - optimized) / baseline * 100
        if baseline > 0 else 0
    )

    print("=" * 65)
    print("2-OPT OPTIMIZATION CHECK")
    print("=" * 65)

    print(f"Orders: {len(customers)}")
    print(f"FCFS distance     : {baseline:.2f} km")
    print(f"2-opt distance    : {optimized:.2f} km")
    print(f"Distance reduction: {result['improvement_km']:.2f} km")
    print(f"Reduction (%)     : {reduction:.2f}%")

    print("\nOptimized delivery order:")
    print("-" * 65)

    # Match optimized coordinates back to order IDs.
    coord_to_order = {
        (float(row.latitude), float(row.longitude)): row.order_id
        for row in df.itertuples()
    }

    for seq, point in enumerate(result["customers"], start=1):
        print(f"{seq:02d}. {coord_to_order[point]}")

    print("=" * 65)

    if optimized <= baseline:
        print("PASS: 2-opt did not increase the route distance.")
    else:
        print("FAIL: optimized route is longer than FCFS.")


if __name__ == "__main__":
    main()
