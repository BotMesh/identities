#!/usr/bin/env python3
"""Task management CLI.

Usage:
  task.py add --title "send the estimate" [--project website] [--due 2026-08-29] [--from-lead L-...]
  task.py status --id T-... --to doing|blocked|done|cancelled [--note "waiting on review"]
  task.py due --id T-... --to 2026-09-05
  task.py list [--status todo] [--project X] [--due-within 7]
  task.py report          # digest for the daily follow-up cron
"""
import argparse

import bizlib

STATUSES = ("todo", "doing", "blocked", "done", "cancelled")


def add(a, con):
    if not a.title:
        bizlib.fail("title is required")
    tid = bizlib.seq_id(con, "T", "tasks", "%Y%m%d")
    ts = bizlib.iso()
    con.execute(
        "INSERT INTO tasks (id,title,project,status,due,from_lead,created_at,updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (tid, a.title, a.project, "todo", a.due, a.from_lead, ts, ts))
    con.commit()
    bizlib.ok({"task": dict(con.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone())})


def status(a, con):
    if a.to not in STATUSES:
        bizlib.fail(f"invalid status {a.to!r}")
    if a.to == "blocked" and not a.note:
        bizlib.fail("blocked requires --note with the blocker reason")
    r = con.execute("SELECT * FROM tasks WHERE id=?", (a.id,)).fetchone()
    if r is None:
        bizlib.fail(f"task {a.id} not found")
    ts = bizlib.iso()
    done_at = ts if a.to == "done" else r["done_at"]
    con.execute("UPDATE tasks SET status=?, updated_at=?, done_at=? WHERE id=?",
                (a.to, ts, done_at, a.id))
    con.commit()
    out = {"task": dict(con.execute("SELECT * FROM tasks WHERE id=?", (a.id,)).fetchone())}
    if a.note:
        out["note"] = a.note
    if a.to == "done" and r["from_lead"]:
        out["remind"] = (f"Task done — append an entry to lead {r['from_lead']}'s "
                         f"timeline via crm-leads upsert_lead.py --timeline.")
    bizlib.ok(out)


def due(a, con):
    con.execute("UPDATE tasks SET due=?, updated_at=? WHERE id=?",
                (a.to, bizlib.iso(), a.id))
    con.commit()
    bizlib.ok({"task": dict(con.execute("SELECT * FROM tasks WHERE id=?", (a.id,)).fetchone())})


def list_(a, con):
    q, args = "SELECT * FROM tasks WHERE 1=1", []
    if a.status:
        q += " AND status=?"; args.append(a.status)
    if a.project:
        q += " AND project=?"; args.append(a.project)
    if a.due_within:
        q += " AND due IS NOT NULL AND due <= date('now', ?)"
        args.append(f"+{a.due_within} days")
    q += " ORDER BY due IS NULL, due, updated_at DESC"
    bizlib.ok({"tasks": [dict(r) for r in con.execute(q, args).fetchall()]})


def report(_a, con):
    today = bizlib.now().strftime("%Y-%m-%d")
    sec = {
        "due_today": con.execute(
            "SELECT * FROM tasks WHERE status IN ('todo','doing') AND due=?",
            (today,)).fetchall(),
        "overdue": con.execute(
            "SELECT * FROM tasks WHERE status IN ('todo','doing') AND due<?",
            (today,)).fetchall(),
        "stalled_over_3_days": con.execute(
            "SELECT * FROM tasks WHERE status='doing' AND updated_at<datetime('now','-3 days')"
        ).fetchall(),
        "blocked": con.execute("SELECT * FROM tasks WHERE status='blocked'").fetchall(),
    }
    bizlib.ok({k: [dict(r) for r in v] for k, v in sec.items()})


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("--title"); s.add_argument("--project")
    s.add_argument("--due"); s.add_argument("--from-lead")
    s = sub.add_parser("status"); s.add_argument("--id", required=True)
    s.add_argument("--to", required=True); s.add_argument("--note")
    s = sub.add_parser("due"); s.add_argument("--id", required=True)
    s.add_argument("--to", required=True)
    s = sub.add_parser("list"); s.add_argument("--status"); s.add_argument("--project")
    s.add_argument("--due-within", type=int)
    sub.add_parser("report")
    a = p.parse_args()
    con = bizlib.connect()
    {"add": add, "status": status, "due": due, "list": list_, "report": report}[a.cmd](a, con)
    con.close()


if __name__ == "__main__":
    main()
