from pathlib import Path
import pandas as pd

from services.fcfs import build_fcfs_route


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "sample_orders.csv"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cannot find dataset: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    result = build_fcfs_route(df)

    print("=" * 65)
    print("FCFS BASELINE CHECK")
    print("=" * 65)
    print(f"Orders: {len(result['orders'])}")
    print(
        f"Hub: ({result['hub'][0]:.6f}, "
        f"{result['hub'][1]:.6f})"
    )

    print("\nFCFS delivery order:")
    print("-" * 65)

    for leg in result["legs"]:
        print(
            f"{leg['sequence']:02d}. "
            f"{leg['order_id']} -> {leg['customer_id']} | "
            f"{leg['distance_from_previous_km']:.2f} km"
        )

    print("\n" + "=" * 65)
    print(
        f"TOTAL FCFS DISTANCE: "
        f"{result['total_distance_km']:.2f} km"
    )
    print("=" * 65)


if __name__ == "__main__":
    main()
