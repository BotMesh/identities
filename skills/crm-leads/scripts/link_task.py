#!/usr/bin/env python3
"""Create a follow-up task from a lead's next_action (linked both ways).

Usage: link_task.py --lead L-acme-jane [--title "send the estimate"] [--due 2026-09-02]
"""
import argparse

import bizlib


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lead", required=True)
    p.add_argument("--title")
    p.add_argument("--due")
    a = p.parse_args()

    con = bizlib.connect()
    lead = con.execute("SELECT * FROM leads WHERE id = ?", (a.lead,)).fetchone()
    if lead is None:
        bizlib.fail(f"lead {a.lead} not found")
    title = a.title or lead["next_action"]
    if not title:
        bizlib.fail("no title given and the lead has no next_action")
    tid = bizlib.seq_id(con, "T", "tasks", "%Y%m%d")
    ts = bizlib.iso()
    con.execute(
        "INSERT INTO tasks (id, title, project, status, due, from_lead,"
        " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (tid, f"{title} ({lead['company']})", "crm-followup", "todo",
         a.due or lead["next_due"], a.lead, ts, ts))
    con.commit()
    row = dict(con.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone())
    con.close()
    bizlib.ok({"task": row})


if __name__ == "__main__":
    main()
