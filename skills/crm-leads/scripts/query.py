#!/usr/bin/env python3
"""Canned lead queries (exact stats go through SQL, never estimated).

Usage:
  query.py --recent 7          # leads updated in the last N days
  query.py --stage qualified   # by stage
  query.py --by-value          # open leads by value, descending
  query.py --lead L-...        # one lead, full row
  query.py --fts estimate      # full-text search
"""
import argparse

import bizlib


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--recent", type=int)
    p.add_argument("--stage")
    p.add_argument("--by-value", action="store_true")
    p.add_argument("--lead")
    p.add_argument("--fts")
    a = p.parse_args()

    con = bizlib.connect()
    if a.lead:
        r = con.execute("SELECT * FROM leads WHERE id = ?", (a.lead,)).fetchone()
        bizlib.ok({"lead": dict(r) if r else None})
    elif a.fts:
        rows = con.execute(
            "SELECT ref_id, kind FROM kb_fts WHERE kb_fts MATCH ? LIMIT 20",
            (a.fts,)).fetchall()
        bizlib.ok({"matches": [dict(r) for r in rows]})
    elif a.by_value:
        rows = con.execute(
            "SELECT * FROM leads WHERE stage NOT IN ('won','lost')"
            " ORDER BY value_cny IS NULL, value_cny DESC").fetchall()
        bizlib.ok({"leads": [dict(r) for r in rows]})
    elif a.stage:
        rows = con.execute("SELECT * FROM leads WHERE stage = ?"
                           " ORDER BY updated_at DESC", (a.stage,)).fetchall()
        bizlib.ok({"leads": [dict(r) for r in rows]})
    else:
        days = a.recent or 7
        rows = con.execute(
            "SELECT * FROM leads WHERE updated_at >= date('now', ?)"
            " ORDER BY updated_at DESC", (f"-{days} days",)).fetchall()
        bizlib.ok({"leads": [dict(r) for r in rows]})
    con.close()


if __name__ == "__main__":
    main()
