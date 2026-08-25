#!/usr/bin/env python3
"""Create or update a lead; renders its markdown file and the index.

Usage:
  upsert_lead.py --company Acme [--contact "Jane Lee"] [--title "Head of Procurement"]
    [--stage qualified] [--value-cny 400000] [--next-action "send the estimate"]
    [--next-due 2026-09-02] [--source voice-2026-08-25]
    [--timeline "first visit, interested in plan B"] [--id L-...]
"""
import argparse

import bizlib

STAGES = ("new", "contacted", "qualified", "proposal", "won", "lost")


def render_md(con, lid):
    r = con.execute("SELECT * FROM leads WHERE id = ?", (lid,)).fetchone()
    path = bizlib.BIZ_HOME / "leads" / f"{lid}.md"
    front = [
        "---",
        f"id: {r['id']}",
        f"company: {r['company']}",
        f"contact: {r['contact'] or ''}",
        f"title: {r['title'] or ''}",
        f"stage: {r['stage']}",
        f"value_cny: {r['value_cny'] if r['value_cny'] is not None else ''}",
        f"next_action: {r['next_action'] or ''}",
        f"next_due: {r['next_due'] or ''}",
        f"updated_at: {r['updated_at']}",
        "---",
        "",
        "## Timeline",
    ]
    if path.exists():
        body = path.read_text(encoding="utf-8")
        timeline = body.split("## Timeline", 1)
        tail = timeline[1].lstrip("\n") if len(timeline) == 2 else ""
    else:
        tail = ""
    path.write_text("\n".join(front) + "\n" + tail, encoding="utf-8")
    return path


def append_timeline(lid, text):
    path = bizlib.BIZ_HOME / "leads" / f"{lid}.md"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- {bizlib.iso()[:10]} {text}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id")
    p.add_argument("--company")
    p.add_argument("--contact")
    p.add_argument("--title")
    p.add_argument("--stage", choices=STAGES)
    p.add_argument("--value-cny", type=int)
    p.add_argument("--next-action")
    p.add_argument("--next-due")
    p.add_argument("--source")
    p.add_argument("--timeline", help="append a timeline entry")
    a = p.parse_args()

    con = bizlib.connect()
    lid = a.id
    existing = con.execute("SELECT * FROM leads WHERE id = ?", (lid,)).fetchone() if lid else None

    if existing is None:
        if not a.company:
            bizlib.fail("company is required to create a lead "
                        "(high-risk field, must be stated explicitly)")
        lid = lid or bizlib.lead_id(a.company, a.contact)
        dup = con.execute("SELECT id FROM leads WHERE id = ?", (lid,)).fetchone()
        if dup:
            existing = con.execute("SELECT * FROM leads WHERE id = ?", (lid,)).fetchone()

    ts = bizlib.iso()
    if existing is None:
        con.execute(
            "INSERT INTO leads (id, company, contact, title, stage, value_cny,"
            " next_action, next_due, source, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (lid, a.company, a.contact, a.title, a.stage or "new", a.value_cny,
             a.next_action, a.next_due, a.source, ts, ts))
        action = "created"
    else:
        fields = {k: v for k, v in {
            "company": a.company, "contact": a.contact, "title": a.title,
            "stage": a.stage, "value_cny": a.value_cny,
            "next_action": a.next_action, "next_due": a.next_due,
        }.items() if v is not None}
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            con.execute(f"UPDATE leads SET {sets}, updated_at = ? WHERE id = ?",
                        (*fields.values(), ts, lid))
        action = "updated"

    row = con.execute("SELECT * FROM leads WHERE id = ?", (lid,)).fetchone()
    bizlib.fts_upsert(con, lid, "lead", " ".join(
        str(row[k] or "") for k in ("company", "contact", "title", "next_action")))
    con.commit()
    path = render_md(con, lid)
    if a.timeline:
        append_timeline(lid, a.timeline)

    # refresh the generated index
    import render_index
    render_index.render_leads(con)
    con.close()
    bizlib.ok({"action": action, "lead": dict(row), "file": str(path)})


if __name__ == "__main__":
    main()
