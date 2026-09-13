import sqlite3
from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "last_mile_co2.db"
)


def check(name, condition, detail):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return condition


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("=" * 70)
    print("CORE 1 — ROUTE VALIDATION")
    print("=" * 70)

    # 1. Orders
    orders = conn.execute(
        "SELECT COUNT(*) AS n FROM orders"
    ).fetchone()["n"]

    check(
        "Orders exist",
        orders > 0,
        f"{orders} orders",
    )

    # 2. Routes
    routes = conn.execute(
        """
        SELECT route_id, batch_id, route_type, distance_km, co2_kg
        FROM routes
        ORDER BY route_id
        """
    ).fetchall()

    check(
        "Routes exist",
        len(routes) > 0,
        f"{len(routes)} routes",
    )

    # 3. One FCFS + one OPTIMIZED per batch
    duplicate_groups = conn.execute(
        """
        SELECT batch_id, vehicle_id, route_type, COUNT(*) AS n
        FROM routes
        GROUP BY batch_id, vehicle_id, route_type
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    check(
        "No duplicate route types",
        len(duplicate_groups) == 0,
        "No duplicate batch/vehicle/route_type groups"
        if not duplicate_groups
        else f"{len(duplicate_groups)} duplicate groups",
    )

    # 4. Validate each route
    for route in routes:
        route_id = route["route_id"]
        route_type = route["route_type"]
        batch_id = route["batch_id"]

        stop_count = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM route_stops
            WHERE route_id = ?
            """,
            (route_id,),
        ).fetchone()["n"]

        batch_order_count = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM orders
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()["n"]

        check(
            f"Route {route_id} stop count",
            stop_count == batch_order_count,
            f"{route_type}: {stop_count} stops / {batch_order_count} batch orders",
        )

        # No duplicate sequence numbers.
        duplicate_sequences = conn.execute(
            """
            SELECT sequence, COUNT(*) AS n
            FROM route_stops
            WHERE route_id = ?
            GROUP BY sequence
            HAVING COUNT(*) > 1
            """,
            (route_id,),
        ).fetchall()

        check(
            f"Route {route_id} unique sequences",
            len(duplicate_sequences) == 0,
            "Sequence numbers are unique",
        )

        # No duplicate orders inside one route.
        duplicate_orders = conn.execute(
            """
            SELECT order_id, COUNT(*) AS n
            FROM route_stops
            WHERE route_id = ?
              AND order_id IS NOT NULL
            GROUP BY order_id
            HAVING COUNT(*) > 1
            """,
            (route_id,),
        ).fetchall()

        check(
            f"Route {route_id} unique orders",
            len(duplicate_orders) == 0,
            "No order appears twice",
        )

        # Distance must be non-negative.
        bad_distance = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM route_stops
            WHERE route_id = ?
              AND distance_from_previous < 0
            """,
            (route_id,),
        ).fetchone()["n"]

        check(
            f"Route {route_id} stop distances",
            bad_distance == 0,
            "All segment distances are >= 0",
        )

        # Route summary values must be non-negative.
        check(
            f"Route {route_id} summary",
            route["distance_km"] >= 0 and route["co2_kg"] >= 0,
            f"distance={route['distance_km']:.2f} km, "
            f"co2={route['co2_kg']:.2f} kg",
        )

    # 5. FCFS vs optimized
    batches = conn.execute(
        """
        SELECT DISTINCT batch_id
        FROM routes
        ORDER BY batch_id
        """
    ).fetchall()

    for batch in batches:
        batch_id = batch["batch_id"]

        fcfs = conn.execute(
            """
            SELECT distance_km, co2_kg
            FROM routes
            WHERE batch_id = ?
              AND route_type = 'FCFS'
            ORDER BY route_id DESC
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()

        optimized = conn.execute(
            """
            SELECT distance_km, co2_kg
            FROM routes
            WHERE batch_id = ?
              AND route_type = 'OPTIMIZED'
            ORDER BY route_id DESC
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()

        if fcfs and optimized:
            check(
                f"Batch {batch_id} optimization",
                optimized["distance_km"] <= fcfs["distance_km"] + 1e-9,
                f"FCFS={fcfs['distance_km']:.2f} km | "
                f"OPTIMIZED={optimized['distance_km']:.2f} km",
            )

    print("=" * 70)
    print("Validation finished.")
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()
