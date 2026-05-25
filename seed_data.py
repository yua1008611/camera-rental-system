import sqlite3
from datetime import date, timedelta
from pathlib import Path

from init_db import init_database


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "camera_rental.db"


def days_between(start, end):
    return (end - start).days + 1


def insert_rental(conn, user_id, camera_id, start, end, daily_price, paid, payment, returned):
    rental_days = days_between(start, end)
    amount_due = rental_days * daily_price
    conn.execute(
        """
        INSERT INTO rentals (
            user_id, camera_id, start_date, end_date, rental_days, daily_price,
            amount_due, amount_paid, payment_status, return_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            camera_id,
            start.isoformat(),
            end.isoformat(),
            rental_days,
            daily_price,
            amount_due,
            paid,
            payment,
            returned,
        ),
    )


def sync_camera_status(conn):
    today = date.today().isoformat()
    camera_ids = [row[0] for row in conn.execute("SELECT id FROM cameras")]
    for camera_id in camera_ids:
        status = conn.execute("SELECT status FROM cameras WHERE id = ?", (camera_id,)).fetchone()[0]
        if status == "维修中":
            continue

        active_unreturned = conn.execute(
            """
            SELECT COUNT(*)
            FROM rentals
            WHERE camera_id = ?
              AND return_status = '未归还'
              AND start_date <= ?
            """,
            (camera_id, today),
        ).fetchone()[0]
        if active_unreturned:
            conn.execute("UPDATE cameras SET status = '已租' WHERE id = ?", (camera_id,))
            continue

        future_unreturned = conn.execute(
            """
            SELECT COUNT(*)
            FROM rentals
            WHERE camera_id = ?
              AND return_status = '未归还'
              AND start_date > ?
            """,
            (camera_id, today),
        ).fetchone()[0]
        if future_unreturned:
            conn.execute("UPDATE cameras SET status = '已预定' WHERE id = ?", (camera_id,))
        else:
            conn.execute(
                "UPDATE cameras SET status = '可租' WHERE id = ? AND status IN ('已租', '已预定')",
                (camera_id,),
            )


def seed():
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            print("已有数据，未重复插入测试数据。")
            return

        users = [
            ("张三", "13800000001", "学生摄影社成员"),
            ("李四", "13800000002", "短视频拍摄"),
            ("王五", "13800000003", "婚礼跟拍"),
        ]
        conn.executemany("INSERT INTO users (name, phone, note) VALUES (?, ?, ?)", users)

        cameras = [
            ("Canon", "EOS R6 Mark II", 180, "可租"),
            ("Sony", "A7M4", 200, "可租"),
            ("Nikon", "Z6 II", 160, "维修中"),
            ("Fujifilm", "X-T5", 150, "可租"),
        ]
        conn.executemany(
            "INSERT INTO cameras (brand, model, daily_price, status) VALUES (?, ?, ?, ?)",
            cameras,
        )

        today = date.today()
        insert_rental(conn, 1, 1, today - timedelta(days=12), today - timedelta(days=10), 180, 540, "已支付", "已归还")
        insert_rental(conn, 2, 2, today - timedelta(days=4), today - timedelta(days=1), 200, 0, "未支付", "未归还")
        insert_rental(conn, 3, 4, today - timedelta(days=8), today - timedelta(days=6), 150, 450, "已支付", "已归还")

        sync_camera_status(conn)
        conn.commit()
        print("测试数据已插入。")


if __name__ == "__main__":
    seed()
