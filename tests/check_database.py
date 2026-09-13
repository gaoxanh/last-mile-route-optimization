from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "database" / "last_mile_co2.db"


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Put the writable SQLite database created from schema.sql "
            "at this path before running this check."
        )

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    print("=" * 65)
    print("DATABASE CHECK")
    print("=" * 65)
    print(f"Database: {DB_PATH}")

    for table in [
        "hubs",
        "customers",
        "vehicles",
        "delivery_batches",
        "orders",
        "routes",
        "route_stops",
    ]:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"{table:20s}: {count}")

    connection.close()
    print("=" * 65)


if __name__ == "__main__":
    main()
