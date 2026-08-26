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
    # Cho phép truy cập cột bằng tên thay vì chỉ số (dict-like)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Đọc file schema.sql và khởi tạo cơ sở dữ liệu."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Không tìm thấy file schema tại: {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()
    print("Khởi tạo Database thành công!")


if __name__ == "__main__":
    init_db()