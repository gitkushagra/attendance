from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hours.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-in-production"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'working',
                start_time TEXT,
                exit_time TEXT,
                extra_working INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, work_date),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        db.commit()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def monday_of(d):
    return d - timedelta(days=d.weekday())


def time_to_minutes(value):
    if not value:
        return None
    try:
        h, m = map(int, value.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return h * 60 + m
    except (ValueError, AttributeError):
        return None


def format_minutes(minutes):
    minutes = max(0, int(round(minutes)))
    return f"{minutes // 60}h {minutes % 60:02d}m"


def format_time_12(value):
    if not value:
        return "—"
    minutes = time_to_minutes(value)
    if minutes is None:
        return value
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def get_log(user_id, work_date):
    with get_db() as db:
        row = db.execute("""
            SELECT * FROM daily_logs
            WHERE user_id = ? AND work_date = ?
        """, (user_id, work_date.isoformat())).fetchone()
    return row


def calculate_week(user_id, week_start):
    # Monday-Friday only. Weekly requirement = 45h minus genuine
    # holiday/leave days. WFH remains a normal 9h working day.
    work_dates = [week_start + timedelta(days=i) for i in range(5)]
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM daily_logs
            WHERE user_id = ? AND work_date BETWEEN ? AND ?
        """, (user_id, work_dates[0].isoformat(), work_dates[-1].isoformat())).fetchall()
    rows_by_date = {r["work_date"]: r for r in rows}

    required = 45 * 60
    for d in work_dates:
        row = rows_by_date.get(d.isoformat())
        if row and row["status"] in {"holiday", "leave"} and not row["extra_working"]:
            required -= 9 * 60
    required = max(0, required)

    worked = 0
    info = {}
    remaining_days = []

    for d in work_dates:
        row = rows_by_date.get(d.isoformat())
        status = row["status"] if row else "working"
        extra = bool(row["extra_working"]) if row else False
        is_working = status in {"working", "wfh"} or (status in {"holiday","leave"} and extra)
        start = (row["start_time"] if row else "") or ""
        exit_time = (row["exit_time"] if row else "") or ""
        actual = None
        sm, em = time_to_minutes(start), time_to_minutes(exit_time)
        if is_working and sm is not None and em is not None:
            actual = em - sm
            if actual < 0: actual += 1440
        info[d] = dict(row=row,status=status,extra_working=extra,is_working=is_working,
                       start=start,exit=exit_time,actual=actual)
        if actual is not None:
            worked += actual
        elif is_working:
            remaining_days.append(d)

    remaining = max(0, required - worked)
    average = remaining / len(remaining_days) if remaining_days else 0

    days=[]
    for d in work_dates:
        x=info[d]
        target = 9*60 if x["actual"] is not None and x["is_working"] else (average if x["is_working"] else 0)
        days.append({
            "date":d,"date_key":d.isoformat(),"weekday":d.strftime("%a"),
            "date_label":d.strftime("%d %b"),"status":x["status"],
            "start":x["start"],"exit":x["exit"],"actual":x["actual"],
            "target":target,
            "difference":None if x["actual"] is None else x["actual"]-target,
            "extra_working":x["extra_working"],"is_working":x["is_working"]
        })

    return {
        "required":required,"worked":worked,"balance":worked-required,
        "left":max(0,required-worked),
        "remaining_working_days":len(remaining_days),
        "average_remaining":average,"days":days
    }


@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    requested_week = parse_date(request.args.get("week"))
    if requested_week:
        week_start = monday_of(requested_week)
    else:
        try:
            selected_year = int(request.args.get("year", date.today().year))
            selected_month = min(12, max(1, int(request.args.get("month", date.today().month))))
            week_of_month = min(5, max(1, int(request.args.get("week_of_month", 1))))

            first_day = date(selected_year, selected_month, 1)
            days_to_monday = (7 - first_day.weekday()) % 7
            first_monday = first_day + timedelta(days=days_to_monday)
            # Week 1 is the first complete Monday-Friday work week whose
            # Monday falls in the selected month. Every selected week is
            # therefore guaranteed to start Monday and end Friday.
            week_start = first_monday + timedelta(weeks=week_of_month - 1)
        except (ValueError, TypeError):
            week_start = monday_of(date.today())
    data = calculate_week(user["id"], week_start)

    return render_template(
        "index.html",
        user=user,
        week_start=week_start,
        week_end=week_start + timedelta(days=4),
        data=data,
        format_minutes=format_minutes,
        format_time_12=format_time_12,
        today=date.today().isoformat(),
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3:
            flash("Username must contain at least 3 characters.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("register.html")

        try:
            with get_db() as db:
                cursor = db.execute("""
                    INSERT INTO users (username, password_hash, created_at)
                    VALUES (?, ?, ?)
                """, (
                    username,
                    generate_password_hash(password),
                    datetime.utcnow().isoformat(),
                ))
                db.commit()
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
            return render_template("register.html")

        session["user_id"] = user_id
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/day/save", methods=["POST"])
def save_day():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Authentication required."}), 401

    work_date = parse_date(request.form.get("work_date"))
    status = request.form.get("status", "working")
    start = request.form.get("start_time", "").strip()
    exit_time = request.form.get("exit_time", "").strip()
    extra_working = 1 if request.form.get("extra_working") == "1" else 0

    if not work_date:
        flash("Invalid date.", "error")
        return redirect(url_for("index"))

    allowed_statuses = {"working", "wfh", "holiday", "leave"}
    if status not in allowed_statuses:
        flash("Invalid day status.", "error")
        return redirect(url_for("index"))

    # The "mark non-working day as working" override is valid only for
    # Holiday/Leave. Working and WFH days must never carry the override.
    if status in {"working", "wfh"}:
        extra_working = 0

    if status == "wfh" or extra_working:
        start = "10:00"
        exit_time = "19:00"
    elif status == "working":
        if start and time_to_minutes(start) is None:
            flash("Invalid start time.", "error")
            return redirect(url_for("index"))
        if exit_time and time_to_minutes(exit_time) is None:
            flash("Invalid exit time.", "error")
            return redirect(url_for("index"))
    else:
        start = ""
        exit_time = ""

    with get_db() as db:
        db.execute("""
            INSERT INTO daily_logs
                (user_id, work_date, status, start_time, exit_time, extra_working)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, work_date)
            DO UPDATE SET
                status=excluded.status,
                start_time=excluded.start_time,
                exit_time=excluded.exit_time,
                extra_working=excluded.extra_working
        """, (
            user["id"], work_date.isoformat(), status, start, exit_time, extra_working
        ))
        db.commit()

    flash("Day updated successfully.", "success")
    return redirect(url_for("index", week=work_date.isoformat()))


@app.route("/api/week")
def api_week():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    requested_week = parse_date(request.args.get("week"))
    week_start = monday_of(requested_week or date.today())
    data = calculate_week(user["id"], week_start)

    return jsonify({
        "week_start": week_start.isoformat(),
        "required": data["required"],
        "worked": data["worked"],
        "balance": data["balance"],
        "left": data["left"],
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
