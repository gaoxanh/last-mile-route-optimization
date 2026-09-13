import sqlite3

from services.database import save_route


def test_save_route(tmp_path):
    db = tmp_path / "test.db"
    connection = sqlite3.connect(db)

    connection.executescript("""
    CREATE TABLE routes (
        route_id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        vehicle_id INTEGER NOT NULL,
        route_type TEXT NOT NULL,
        distance_km REAL,
        co2_kg REAL
    );

    CREATE TABLE route_stops (
        route_stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL,
        sequence INTEGER NOT NULL,
        order_id INTEGER,
        distance_from_previous REAL
    );
    """)

    route_id = save_route(
        connection=connection,
        batch_id=1,
        vehicle_id=1,
        route_type="FCFS",
        distance_km=10.5,
        co2_kg=0.63,
        stops=[
            {
                "sequence": 1,
                "order_id": 1,
                "distance_from_previous_km": 3.2,
            },
            {
                "sequence": 2,
                "order_id": 2,
                "distance_from_previous_km": 7.3,
            },
        ],
    )

    assert route_id == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM routes"
    ).fetchone()[0] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM route_stops"
    ).fetchone()[0] == 2

    connection.close()
