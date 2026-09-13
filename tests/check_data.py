import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database.connection import get_connection


def print_table(cursor, table_name):
    """In toàn bộ nội dung của một bảng dưới dạng định dạng đẹp."""
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    print(f"\n==================== BẢNG: {table_name.upper()} ({len(rows)} bản ghi) ====================")
    if not rows:
        print("(Trống)")
        return

    # Lấy tên các cột
    headers = rows[0].keys()
    print(" | ".join(f"{h:<15}" for h in headers))
    print("-" * (18 * len(headers)))

    # In từng dòng
    for row in rows:
        print(" | ".join(f"{str(row[h]):<15}" for h in headers))


def main():
    conn = get_connection()
    cursor = conn.cursor()

    # Danh sách các bảng cần kiểm tra
    tables = ["hubs", "vehicles", "delivery_batches", "customers", "orders", "routes", "route_stops"]

    for table in tables:
        print_table(cursor, table)

    conn.close()


if __name__ == "__main__":
    main()