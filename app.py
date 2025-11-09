from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import sqlite3, os
from flask import Flask, render_template, request, redirect, url_for

DB = "countdown.db"
TZ = ZoneInfo("Europe/Berlin")
app = Flask(__name__)

def _init_db():
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS cfg (
                     id INTEGER PRIMARY KEY CHECK (id=1),
                     title TEXT,
                     target_utc TEXT,
                     start_utc TEXT
        )""")

def get_cfg():
    with sqlite3.connect(DB) as c:
        row = c.execute("SELECT title, target_utc, start_utc FROM cfg WHERE id=1").fetchone()
    if not row:
        return "Noch kein Ziel", None, None
    title = row[0] or "Countdown"
    target = datetime.fromisoformat(row[1]).replace(tzinfo=timezone.utc) if row[1] else None
    start = datetime.fromisoformat(row[2]).replace(tzinfo=timezone.utc) if row[2] else None
    return title, target, start

def set_cfg(title, target_local, start_local):
    target_utc = target_local.astimezone(timezone.utc).isoformat()
    start_utc = start_local.astimezone(timezone.utc).isoformat()
    with sqlite3.connect(DB) as c:
        c.execute(
            """INSERT INTO cfg(id,title,target_utc,start_utc)
               VALUES(1,?,?,?)
               ON CONFLICT(id) DO UPDATE
               SET title=excluded.title,
                   target_utc=excluded.target_utc,
                   start_utc=excluded.start_utc""",
            (title, target_utc, start_utc),
        )

@app.route("/")
def index():
    title, target, start = get_cfg()
    now = datetime.now(timezone.utc)

    days_remaining = None
    days_elapsed = None
    days_total = None
    percent = None

    if target:
        delta = target - now
        seconds = max(0, int(delta.total_seconds()))
        days_remaining = seconds // 86400
        hours_remaining = (((seconds + 86400 - 1) % 86400) // 60) // 60
        minutes_remaining = ((seconds + 86400 - 1) // 60) % 60

    if start and target:
        total_sec = max(0, (target - start).total_seconds())
        elapsed_sec = (now - start).total_seconds()
        elapsed_sec = max(0, min(elapsed_sec, total_sec))  # clamp
        if total_sec > 0:
            percent = round(100 * (elapsed_sec / total_sec), 1)
        else:
            percent = 100.0

        days_total = (int(total_sec) + 86400 - 1) // 86400 if total_sec > 0 else 0
        days_elapsed = min(days_total, int(elapsed_sec) // 86400)

    return render_template(
        "index.html",
        title=title,
        target=target,
        start=start,
        days_remaining=days_remaining,
        hours_remaining=hours_remaining,
        minutes_remaining=minutes_remaining,
        days_elapsed=days_elapsed,
        days_total=days_total,
        percent=percent,
    )

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = (request.form.get("title") or "Countdown").strip()
        dt_target_str = request.form["datetime_target"]
        dt_start_str = request.form["datetime_start"]

        target_local = datetime.fromisoformat(dt_target_str).replace(tzinfo=TZ)
        start_local = datetime.fromisoformat(dt_start_str).replace(tzinfo=TZ)

        if start_local > target_local:
            start_local, target_local = target_local, start_local

        set_cfg(title, target_local, start_local)
        return redirect(url_for("index"))
    return render_template("admin.html")

if __name__ == "__main__":
    _init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

