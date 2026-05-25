import sqlite3
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "camera_rental.db"))


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    daily_price REAL NOT NULL CHECK (daily_price >= 0),
    status TEXT NOT NULL DEFAULT '可租'
        CHECK (status IN ('可租', '已租', '已预定', '维修中'))
);

CREATE TABLE IF NOT EXISTS rentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    camera_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    rental_days INTEGER NOT NULL CHECK (rental_days > 0),
    daily_price REAL NOT NULL CHECK (daily_price >= 0),
    amount_due REAL NOT NULL CHECK (amount_due >= 0),
    amount_paid REAL NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    payment_status TEXT NOT NULL CHECK (payment_status IN ('已支付', '未支付')),
    return_status TEXT NOT NULL CHECK (return_status IN ('已归还', '未归还')),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE RESTRICT
);
"""


def migrate_camera_status_values(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'cameras'"
    ).fetchone()
    if not row or "已预定" in row[0]:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DROP TABLE IF EXISTS cameras_new")
    conn.executescript(
        """
        CREATE TABLE cameras_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            daily_price REAL NOT NULL CHECK (daily_price >= 0),
            status TEXT NOT NULL DEFAULT '可租'
                CHECK (status IN ('可租', '已租', '已预定', '维修中'))
        );

        INSERT INTO cameras_new (id, brand, model, daily_price, status)
        SELECT id, brand, model, daily_price, status FROM cameras;

        DROP TABLE cameras;
        ALTER TABLE cameras_new RENAME TO cameras;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def init_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        migrate_camera_status_values(conn)
        conn.commit()


if __name__ == "__main__":
    init_database()
    print(f"数据库已初始化：{DB_PATH}")
