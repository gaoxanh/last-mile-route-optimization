import os
import sqlite3

# Xác định đường dẫn tương đối chuẩn xác cho cả Local và Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "last_mile_co2.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


def get_connection():
    """Tạo kết nối đến SQLite DB và kích hoạt Foreign Key constraints."""
    # Kết nối ở chế độ Read-Only nếu chạy trên Cloud, giúp tránh lỗi ghi file hệ thống
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    # Cho phép truy cập cột bằng tên thay vì chỉ số (dict-like)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Đọc file schema.sql và khởi tạo cơ sở dữ liệu (Chỉ chạy dưới Local)."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Không tìm thấy file schema tại: {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()
    print("Khởi tạo Database cấu trúc trống thành công!")


def ensure_database_ready():
    """
    Hàm kiểm tra an toàn hệ thống.
    Đảm bảo file database đã tồn tại và sẵn sàng đọc dữ liệu.
    """
    if not os.path.exists(DB_PATH):
        # Nếu chạy trên Cloud mà thiếu file, thông báo để lập trình viên push file lên GitHub
        print(f"⚠️ CẢNH BÁO: Không tìm thấy file dữ liệu tại {DB_PATH}.")
        print("Vui lòng đảm bảo đã push file 'last_mile_co2.db' hoàn chỉnh từ Local lên GitHub.")
    else:
        # Kiểm tra nhanh xem bảng orders đã tồn tại dữ liệu chưa
        try:
            with get_connection() as conn:
                result = conn.execute(
                    "SELECT COUNT(*) FROM orders"
                ).fetchone()

                # Lightweight migration for existing demo DB files.
                route_columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(routes)").fetchall()
                }
                if "urgent_order_id" not in route_columns:
                    conn.execute("ALTER TABLE routes ADD COLUMN urgent_order_id TEXT")
                if "scenario" not in route_columns:
                    conn.execute("ALTER TABLE routes ADD COLUMN scenario TEXT DEFAULT 'Normal'")
                if "duration_min" not in route_columns:
                    conn.execute("ALTER TABLE routes ADD COLUMN duration_min REAL DEFAULT 0.0")
                conn.commit()

                print(f"✅ Hệ thống sẵn sàng. Tổng số đơn hàng hiện tại: {result[0]}")
        except sqlite3.OperationalError:
            print("⚠️ CẢNH BÁO: File DB tồn tại nhưng cấu trúc bảng chưa khớp. Vui lòng chạy init_db dưới Local trước.")


# Tự động kiểm tra trạng thái dữ liệu nền khi module được import
ensure_database_ready()


if __name__ == "__main__":
    # Chỉ thực thi tạo cấu trúc database mới khi chạy độc lập file này dưới máy cá nhân
    init_db()
