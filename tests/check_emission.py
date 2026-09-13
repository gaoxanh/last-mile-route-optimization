from pathlib import Path
import pandas as pd

from services.fcfs import build_fcfs_route
from services.two_opt import optimize_2opt
from services.emission import (
    calculate_co2,
    calculate_reduction_percent,
    DEFAULT_MOTORCYCLE_EMISSION_FACTOR,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "sample_orders.csv"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cannot find dataset: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    # Step 4: FCFS baseline
    fcfs = build_fcfs_route(df)

    # Step 5: 2-opt optimization
    customers = [
        (float(row.latitude), float(row.longitude))
        for row in fcfs["orders"].itertuples()
    ]

    optimized = optimize_2opt(fcfs["hub"], customers)

    baseline_distance = optimized["baseline_distance_km"]
    optimized_distance = optimized["optimized_distance_km"]

    # Step 6: CO2
    factor = DEFAULT_MOTORCYCLE_EMISSION_FACTOR

    baseline_co2 = calculate_co2(baseline_distance, factor)
    optimized_co2 = calculate_co2(optimized_distance, factor)

    distance_reduction = calculate_reduction_percent(
        baseline_distance, optimized_distance
    )
    co2_reduction = calculate_reduction_percent(
        baseline_co2, optimized_co2
    )

    print("=" * 65)
    print("CO2 EMISSION CHECK")
    print("=" * 65)
    print(f"Orders: {len(df)}")
    print(f"Vehicle: Motorcycle")
    print(f"Emission factor: {factor:.2f} kg CO2/km")
    print()
    print(f"FCFS distance     : {baseline_distance:.2f} km")
    print(f"2-opt distance    : {optimized_distance:.2f} km")
    print(f"Distance reduction: {distance_reduction:.2f}%")
    print()
    print(f"FCFS CO2          : {baseline_co2:.2f} kg")
    print(f"2-opt CO2         : {optimized_co2:.2f} kg")
    print(f"CO2 reduction     : {co2_reduction:.2f}%")
    print("=" * 65)


if __name__ == "__main__":
    main()
