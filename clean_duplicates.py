import sqlite3
from pathlib import Path

# Đường dẫn đến file database 
DB_PATH = Path(__file__).resolve().parent / "database/last_mile_co2.db"  

def cleanup_duplicate_routes():
    if not DB_PATH.exists():
        print(f"❌ Không tìm thấy file database tại: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Bật foreign keys để tự động cascade nếu có cấu hình
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Tìm danh sách các route_id bị trùng cần xóa (chỉ giữ lại ID lớn nhất cho mỗi batch + type)
        cursor.execute(
            """
            DELETE FROM routes
            WHERE route_id NOT IN (
                SELECT MAX(route_id)
                FROM routes
                GROUP BY batch_id, vehicle_id, route_type
            );
            """
        )
        deleted_routes = cursor.rowcount

        # 2. Xóa các điểm dừng (route_stops) mồ côi không còn route_id tồn tại
        cursor.execute(
            """
            DELETE FROM route_stops
            WHERE route_id NOT IN (SELECT route_id FROM routes);
            """
        )
        deleted_stops = cursor.rowcount

        conn.commit()
        print(f"✅ Dọn dẹp hoàn tất!")
        print(f"- Đã xóa {deleted_routes} tuyến đường trùng lặp.")
        print(f"- Đã xóa {deleted_stops} điểm dừng liên quan.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Lỗi khi dọn dẹp database: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    cleanup_duplicate_routes()