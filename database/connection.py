import os
import sqlite3

# Đường dẫn tới file DB và Schema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "last_mile_co2.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


def get_connection():
    """Tạo kết nối đến SQLite DB và kích hoạt Foreign Key constraints."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Khởi tạo database từ schema.sql nếu database chưa có tables."""

    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(
            f"Không tìm thấy file schema tại: {SCHEMA_PATH}"
        )

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()


def ensure_database():
    """
    Đảm bảo database đã được khởi tạo và có dữ liệu mẫu.
    Chỉ seed dữ liệu khi database chưa có orders.
    """

    needs_init = not os.path.exists(DB_PATH)

    if not needs_init:
        conn = sqlite3.connect(DB_PATH)

        try:
            result = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table' AND name='orders'
                """
            ).fetchone()

            needs_init = result is None
        finally:
            conn.close()

    # 1. Database chưa có schema
    if needs_init:
        init_db()

    # 2. Database có schema nhưng chưa có orders
    conn = sqlite3.connect(DB_PATH)

    try:
        order_count = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]
    finally:
        conn.close()

    if order_count == 0:
        from data.generator import seed_data_from_csv
        seed_data_from_csv()


# Tự động đảm bảo DB tồn tại trước khi các module sử dụng get_connection()
ensure_database()


if __name__ == "__main__":
    init_db()