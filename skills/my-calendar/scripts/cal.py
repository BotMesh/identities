#!/usr/bin/env python3
"""Calendar and reminders CLI.

Usage:
  cal.py add --title "meet the client" --at "2026-08-26T15:00" [--remind 30]
    [--location "..."] [--lead L-...]
  cal.py list [--days 7]
  cal.py digest             # today's events + due tasks (morning cron)
  cal.py tick [--window 15] # reminders due in the next N minutes; marks reminded
"""
import argparse
from datetime import datetime, timedelta

import bizlib


def parse_at(s):
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        bizlib.fail(f"invalid datetime {s!r}; use ISO format like 2026-08-26T15:00")
    if dt.tzinfo is None and bizlib.ZoneInfo is not None:
        dt = dt.replace(tzinfo=bizlib.ZoneInfo(bizlib.TZ_NAME))
    return dt


def add(a, con):
    dt = parse_at(a.at)
    clash = con.execute(
        "SELECT id,title,starts_at FROM events WHERE date(starts_at)=date(?)",
        (dt.isoformat(),)).fetchall()
    eid = bizlib.seq_id(con, "E", "events", "%Y%m%d")
    con.execute(
        "INSERT INTO events (id,title,starts_at,remind_before_min,location,related_lead)"
        " VALUES (?,?,?,?,?,?)",
        (eid, a.title, dt.isoformat(), a.remind, a.location, a.lead))
    con.commit()
    bizlib.ok({"event": dict(con.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()),
               "same_day_events": [dict(r) for r in clash],
               "note": "Reminder precision is ±15 min (tick interval)."})


def list_(a, con):
    rows = con.execute(
        "SELECT * FROM events WHERE starts_at >= datetime('now','localtime')"
        " AND starts_at <= datetime('now','localtime', ?) ORDER BY starts_at",
        (f"+{a.days or 7} days",)).fetchall()
    bizlib.ok({"events": [dict(r) for r in rows]})


def digest(_a, con):
    today = bizlib.now().strftime("%Y-%m-%d")
    events = con.execute(
        "SELECT * FROM events WHERE date(starts_at)=? ORDER BY starts_at",
        (today,)).fetchall()
    tasks = con.execute(
        "SELECT * FROM tasks WHERE status IN ('todo','doing') AND due=?",
        (today,)).fetchall()
    bizlib.ok({"today": today,
               "events": [dict(r) for r in events],
               "tasks_due": [dict(r) for r in tasks]})


def tick(a, con):
    window = a.window or 15
    now = bizlib.now()
    horizon = (now + timedelta(minutes=window)).isoformat()
    rows = con.execute(
        "SELECT * FROM events WHERE reminded=0 AND"
        " datetime(starts_at, '-' || remind_before_min || ' minutes') <= ?",
        (horizon,)).fetchall()
    fire = [r for r in rows if r["starts_at"] >= now.isoformat()[:16]]
    for r in fire:
        con.execute("UPDATE events SET reminded=1 WHERE id=?", (r["id"],))
    con.commit()
    bizlib.ok({"fire": [dict(r) for r in fire],
               "note": "Send one reminder message per event; if empty, stay silent."})


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("--title", required=True)
    s.add_argument("--at", required=True); s.add_argument("--remind", type=int, default=30)
    s.add_argument("--location"); s.add_argument("--lead")
    s = sub.add_parser("list"); s.add_argument("--days", type=int)
    sub.add_parser("digest")
    s = sub.add_parser("tick"); s.add_argument("--window", type=int)
    a = p.parse_args()
    con = bizlib.connect()
    {"add": add, "list": list_, "digest": digest, "tick": tick}[a.cmd](a, con)
    con.close()


if __name__ == "__main__":
    main()
