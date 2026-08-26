-- Bật tính năng ràng buộc Khóa ngoại (Foreign Keys) cho SQLite
PRAGMA foreign_keys = ON;

-- 1. Bảng Hubs (Kho hàng / Trạm giao nhận)
CREATE TABLE IF NOT EXISTS hubs (
    hub_id STRING PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);

-- 2. Bảng Customers (Khách hàng)
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);

-- 3. Bảng Vehicles (Phương tiện)
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_type TEXT NOT NULL,
    capacity_kg REAL NOT NULL CHECK (capacity_kg > 0),
    emission_factor REAL NOT NULL CHECK (emission_factor >= 0)
);

-- 4. Bảng Delivery Batches (Đợt/Lô giao hàng)
CREATE TABLE IF NOT EXISTS delivery_batches (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hub_id STRING NOT NULL,
    vehicle_id INTEGER NOT NULL,
    delivery_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    FOREIGN KEY (hub_id) REFERENCES hubs(hub_id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE RESTRICT
);

-- 5. Bảng Orders (Đơn hàng)
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    hub_id STRING NOT NULL,
    batch_id INTEGER NOT NULL,
    weight_kg REAL NOT NULL CHECK (weight_kg > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'PENDING',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (hub_id) REFERENCES hubs(hub_id) ON DELETE CASCADE,
    FOREIGN KEY (batch_id) REFERENCES delivery_batches(batch_id) ON DELETE CASCADE
);

-- 6. Bảng Routes (Tuyến đường giao hàng)
CREATE TABLE IF NOT EXISTS routes (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    vehicle_id INTEGER NOT NULL,
    route_type TEXT NOT NULL CHECK (route_type IN ('FCFS', 'OPTIMIZED')),
    distance_km REAL DEFAULT 0.0,
    co2_kg REAL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES delivery_batches(batch_id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE RESTRICT
);

-- 7. Bảng Route Stops (Các điểm dừng trên tuyến đường)
CREATE TABLE IF NOT EXISTS route_stops (
    route_stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    order_id INTEGER,
    distance_from_previous REAL DEFAULT 0.0,
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE SET NULL,
    UNIQUE (route_id, sequence)
);