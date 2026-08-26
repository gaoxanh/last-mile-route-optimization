import csv
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database.connection import get_connection

CSV_PATH = os.path.join(BASE_DIR, "data", "sample_orders.csv")


def extract_number(text_id):
    """Trích xuất số từ mã dạng chuỗi (VD: 'O001' -> 1, 'KH025' -> 25, 'H01' -> 1)."""
    match = re.search(r"\d+", str(text_id))
    return int(match.group()) if match else 1



def seed_data_from_csv():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Không tìm thấy file CSV tại: {CSV_PATH}")

    conn = get_connection()
    cursor = conn.cursor()

    # Dùng 'utf-8-sig' để loại bỏ ký tự BOM (\ufeff)
    with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # 1. XOÁ DỮ LIỆU CŨ ĐỂ KHÔNG BỊ TRÙNG LẮP
        cursor.execute("DELETE FROM route_stops;")
        cursor.execute("DELETE FROM routes;")
        cursor.execute("DELETE FROM orders;")
        cursor.execute("DELETE FROM delivery_batches;")
        cursor.execute("DELETE FROM customers;")
        cursor.execute("DELETE FROM vehicles;")
        cursor.execute("DELETE FROM hubs;")

        # 1. Đọc dòng đầu tiên để lấy tọa độ Hub và khởi tạo Hub/Vehicle/Batch mẫu
        first_row = next(reader)

        hub_num_id = extract_number(first_row.get("hub_id", "1"))
        hub_lat = float(first_row.get("hub_latitude", 10.98))
        hub_lng = float(first_row.get("hub_longitude", 106.65))

        cursor.execute(
            """
            INSERT OR IGNORE INTO hubs (hub_id, name, latitude, longitude)
            VALUES (?, ?, ?, ?)
        """,
            (hub_num_id, first_row.get("hub_id", "H01"), hub_lat, hub_lng),
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO vehicles (vehicle_id, vehicle_type, capacity_kg, emission_factor)
            VALUES (1, 'Motorcycle', 150.0, 0.08)
        """
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO delivery_batches (batch_id, hub_id, vehicle_id, delivery_date, status)
            VALUES (1, ?, 1, '2026-08-21', 'READY')
        """,
            (hub_num_id,),
        )

        # Đưa con trỏ đọc lại từ dòng đầu tiên của CSV
        f.seek(0)
        reader = csv.DictReader(f)

        # 2. Đọc và chèn dữ liệu Khách hàng & Đơn hàng
        for row in reader:
            clean_row = {
                k.strip(): v.strip() for k, v in row.items() if k is not None
            }

            order_str_id = clean_row["order_id"]
            cust_str_id = clean_row["customer_id"]

            order_num_id = extract_number(order_str_id)
            cust_num_id = extract_number(cust_str_id)

            lat = float(clean_row["latitude"])
            lng = float(clean_row["longitude"])
            weight = float(clean_row["weight_kg"])
            created_at = clean_row["created_at"]
            status = clean_row.get("status", "PENDING")

            # Thêm Khách hàng (Lưu mã KH001 làm Tên)
            cursor.execute(
                """
                INSERT OR IGNORE INTO customers (customer_id, name, latitude, longitude)
                VALUES (?, ?, ?, ?)
            """,
                (cust_num_id, cust_str_id, lat, lng),
            )

            # Thêm Đơn hàng
            cursor.execute(
                """
                INSERT OR IGNORE INTO orders (order_id, customer_id, hub_id, batch_id, weight_kg, created_at, status)
                VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
                (
                    order_num_id,
                    cust_num_id,
                    hub_num_id,
                    weight,
                    created_at,
                    status,
                ),
            )

    conn.commit()
    conn.close()
    print(
        "-> Đã nạp thành công 30 đơn hàng từ file sample_orders.csv mới vào Database!"
    )


if __name__ == "__main__":
    seed_data_from_csv()