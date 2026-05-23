import os
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, g, redirect, render_template, request, send_file, url_for

from init_db import DB_PATH, init_database


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "camera-rental-demo-secret")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def calculate_rental(start_date, end_date, daily_price):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    rental_days = (end - start).days + 1
    if rental_days <= 0:
        raise ValueError("结束日期不能早于开始日期")
    amount_due = rental_days * float(daily_price)
    return rental_days, amount_due


def sync_camera_status(camera_id):
    db = get_db()
    unreturned = query_one(
        "SELECT COUNT(*) AS total FROM rentals WHERE camera_id = ? AND return_status = '未归还'",
        (camera_id,),
    )["total"]
    if unreturned:
        db.execute("UPDATE cameras SET status = '已租' WHERE id = ?", (camera_id,))
    else:
        db.execute(
            "UPDATE cameras SET status = '可租' WHERE id = ? AND status = '已租'",
            (camera_id,),
        )


def money(value):
    return f"{float(value or 0):.2f}"


app.jinja_env.filters["money"] = money
init_database()


@app.route("/")
def index():
    stats = {
        "total_orders": query_one("SELECT COUNT(*) AS total FROM rentals")["total"],
        "total_income": query_one("SELECT COALESCE(SUM(amount_paid), 0) AS total FROM rentals")["total"],
        "unpaid_orders": query_one("SELECT COUNT(*) AS total FROM rentals WHERE payment_status = '未支付'")["total"],
        "unreturned_orders": query_one("SELECT COUNT(*) AS total FROM rentals WHERE return_status = '未归还'")["total"],
    }
    recent_rentals = query_all(
        """
        SELECT r.*, u.name AS user_name, c.brand, c.model
        FROM rentals r
        JOIN users u ON r.user_id = u.id
        JOIN cameras c ON r.camera_id = c.id
        ORDER BY r.created_at DESC
        LIMIT 6
        """
    )
    return render_template("index.html", stats=stats, recent_rentals=recent_rentals)


@app.route("/users", methods=["GET", "POST"])
def users():
    db = get_db()
    edit_user = None
    if request.method == "POST":
        user_id = request.form.get("id")
        data = (
            request.form["name"].strip(),
            request.form.get("phone", "").strip(),
            request.form.get("note", "").strip(),
        )
        if user_id:
            db.execute("UPDATE users SET name = ?, phone = ?, note = ? WHERE id = ?", (*data, user_id))
            flash("用户信息已更新。")
        else:
            db.execute("INSERT INTO users (name, phone, note) VALUES (?, ?, ?)", data)
            flash("用户已添加。")
        db.commit()
        return redirect(url_for("users"))

    edit_id = request.args.get("edit")
    if edit_id:
        edit_user = query_one("SELECT * FROM users WHERE id = ?", (edit_id,))
    user_list = query_all("SELECT * FROM users ORDER BY id DESC")
    return render_template("users.html", users=user_list, edit_user=edit_user)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    try:
        get_db().execute("DELETE FROM users WHERE id = ?", (user_id,))
        get_db().commit()
        flash("用户已删除。")
    except sqlite3.IntegrityError:
        flash("该用户已有租赁订单，不能直接删除。")
    return redirect(url_for("users"))


@app.route("/rentals/users", methods=["POST"])
def add_user_from_rentals():
    db = get_db()
    name = request.form["name"].strip()
    phone = request.form.get("phone", "").strip()
    note = request.form.get("note", "").strip()
    if not name:
        flash("请填写用户姓名。")
        return redirect(url_for("rentals"))

    cursor = db.execute(
        "INSERT INTO users (name, phone, note) VALUES (?, ?, ?)",
        (name, phone, note),
    )
    db.commit()
    flash("用户已添加，可以直接创建订单。")
    return redirect(url_for("rentals", user_id=cursor.lastrowid))


@app.route("/cameras", methods=["GET", "POST"])
def cameras():
    db = get_db()
    edit_camera = None
    if request.method == "POST":
        camera_id = request.form.get("id")
        data = (
            request.form["brand"].strip(),
            request.form["model"].strip(),
            float(request.form["daily_price"]),
            request.form["status"],
        )
        if camera_id:
            db.execute(
                "UPDATE cameras SET brand = ?, model = ?, daily_price = ?, status = ? WHERE id = ?",
                (*data, camera_id),
            )
            sync_camera_status(camera_id)
            flash("相机信息已更新。")
        else:
            db.execute(
                "INSERT INTO cameras (brand, model, daily_price, status) VALUES (?, ?, ?, ?)",
                data,
            )
            flash("相机已添加。")
        db.commit()
        return redirect(url_for("cameras"))

    edit_id = request.args.get("edit")
    if edit_id:
        edit_camera = query_one("SELECT * FROM cameras WHERE id = ?", (edit_id,))
    camera_list = query_all("SELECT * FROM cameras ORDER BY id DESC")
    return render_template("cameras.html", cameras=camera_list, edit_camera=edit_camera)


@app.route("/cameras/<int:camera_id>/delete", methods=["POST"])
def delete_camera(camera_id):
    try:
        get_db().execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        get_db().commit()
        flash("相机已删除。")
    except sqlite3.IntegrityError:
        flash("该相机已有租赁订单，不能直接删除。")
    return redirect(url_for("cameras"))


@app.route("/rentals", methods=["GET", "POST"])
def rentals():
    db = get_db()
    edit_rental = None
    if request.method == "POST":
        rental_id = request.form.get("id")
        user_id = request.form["user_id"]
        camera_id = request.form["camera_id"]
        camera = query_one("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        if not camera:
            flash("请选择有效相机。")
            return redirect(url_for("rentals"))

        old_camera_id = None
        if rental_id:
            old = query_one("SELECT * FROM rentals WHERE id = ?", (rental_id,))
            old_camera_id = old["camera_id"] if old else None
            if old_camera_id and int(old_camera_id) != int(camera_id) and camera["status"] != "可租":
                flash("新选择的相机当前不可租，请选择状态为“可租”的相机。")
                return redirect(url_for("rentals"))
        elif camera["status"] != "可租":
            flash("该相机当前不可租，请选择状态为“可租”的相机。")
            return redirect(url_for("rentals"))

        try:
            rental_days, amount_due = calculate_rental(
                request.form["start_date"],
                request.form["end_date"],
                camera["daily_price"],
            )
        except ValueError as exc:
            flash(str(exc))
            return redirect(url_for("rentals"))

        data = (
            user_id,
            camera_id,
            request.form["start_date"],
            request.form["end_date"],
            rental_days,
            camera["daily_price"],
            amount_due,
            float(request.form.get("amount_paid") or 0),
            request.form["payment_status"],
            request.form["return_status"],
        )
        if rental_id:
            db.execute(
                """
                UPDATE rentals
                SET user_id = ?, camera_id = ?, start_date = ?, end_date = ?,
                    rental_days = ?, daily_price = ?, amount_due = ?, amount_paid = ?,
                    payment_status = ?, return_status = ?
                WHERE id = ?
                """,
                (*data, rental_id),
            )
            flash("租赁订单已更新。")
        else:
            db.execute(
                """
                INSERT INTO rentals (
                    user_id, camera_id, start_date, end_date, rental_days, daily_price,
                    amount_due, amount_paid, payment_status, return_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
            flash("租赁订单已创建。")

        sync_camera_status(camera_id)
        if old_camera_id and int(old_camera_id) != int(camera_id):
            sync_camera_status(old_camera_id)
        db.commit()
        return redirect(url_for("rentals"))

    edit_id = request.args.get("edit")
    if edit_id:
        edit_rental = query_one("SELECT * FROM rentals WHERE id = ?", (edit_id,))

    selected_user_id = request.args.get("user_id", "")
    users_list = query_all("SELECT * FROM users ORDER BY name")
    cameras_list = query_all("SELECT * FROM cameras ORDER BY brand, model")
    rental_list = query_all(
        """
        SELECT r.*, u.name AS user_name, c.brand, c.model
        FROM rentals r
        JOIN users u ON r.user_id = u.id
        JOIN cameras c ON r.camera_id = c.id
        ORDER BY r.created_at DESC, r.id DESC
        """
    )
    today = date.today().isoformat()
    return render_template(
        "rentals.html",
        users=users_list,
        cameras=cameras_list,
        rentals=rental_list,
        edit_rental=edit_rental,
        selected_user_id=selected_user_id,
        today=today,
    )


@app.route("/rentals/<int:rental_id>/delete", methods=["POST"])
def delete_rental(rental_id):
    rental = query_one("SELECT * FROM rentals WHERE id = ?", (rental_id,))
    if rental:
        get_db().execute("DELETE FROM rentals WHERE id = ?", (rental_id,))
        sync_camera_status(rental["camera_id"])
        get_db().commit()
        flash("租赁订单已删除。")
    return redirect(url_for("rentals"))


@app.route("/stats")
def stats():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    params = []
    date_where = []
    if start_date:
        date_where.append("start_date >= ?")
        params.append(start_date)
    if end_date:
        date_where.append("end_date <= ?")
        params.append(end_date)
    where_sql = "WHERE " + " AND ".join(date_where) if date_where else ""

    total_income = query_one("SELECT COALESCE(SUM(amount_paid), 0) AS total FROM rentals")["total"]
    range_income = query_one(
        f"SELECT COALESCE(SUM(amount_paid), 0) AS total FROM rentals {where_sql}",
        params,
    )["total"]
    by_user = query_all(
        """
        SELECT u.name, COALESCE(SUM(r.amount_paid), 0) AS total_paid, COUNT(r.id) AS rental_count
        FROM users u
        LEFT JOIN rentals r ON u.id = r.user_id
        GROUP BY u.id
        ORDER BY total_paid DESC
        """
    )
    by_camera = query_all(
        """
        SELECT c.brand, c.model, COUNT(r.id) AS rental_count,
               COALESCE(SUM(r.amount_paid), 0) AS income
        FROM cameras c
        LEFT JOIN rentals r ON c.id = r.camera_id
        GROUP BY c.id
        ORDER BY rental_count DESC, income DESC
        """
    )
    unpaid = query_all(
        """
        SELECT r.*, u.name AS user_name, c.brand, c.model
        FROM rentals r
        JOIN users u ON r.user_id = u.id
        JOIN cameras c ON r.camera_id = c.id
        WHERE r.payment_status = '未支付'
        ORDER BY r.end_date
        """
    )
    unreturned = query_all(
        """
        SELECT r.*, u.name AS user_name, c.brand, c.model
        FROM rentals r
        JOIN users u ON r.user_id = u.id
        JOIN cameras c ON r.camera_id = c.id
        WHERE r.return_status = '未归还'
        ORDER BY r.end_date
        """
    )
    return render_template(
        "stats.html",
        total_income=total_income,
        range_income=range_income,
        by_user=by_user,
        by_camera=by_camera,
        unpaid=unpaid,
        unreturned=unreturned,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/export-db")
def export_db():
    token = os.environ.get("EXPORT_TOKEN")
    if not token or request.args.get("token") != token:
        return "无权下载数据库", 403
    return send_file(DB_PATH, as_attachment=True, download_name="camera_rental.db")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
