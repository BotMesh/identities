#!/usr/bin/env python3
"""Fuzzy-match existing leads before creating a new one (dedupe gate).

Usage: find_lead.py --company Acme [--contact "Jane Lee"]
"""
import argparse

import bizlib


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True)
    p.add_argument("--contact")
    a = p.parse_args()

    con = bizlib.connect()
    like_c = f"%{a.company.strip()}%"
    rows = con.execute(
        "SELECT * FROM leads WHERE company LIKE ? ORDER BY updated_at DESC",
        (like_c,)).fetchall()
    candidates = []
    for r in rows:
        score = 0.6
        if a.contact and r["contact"] and a.contact.strip() in r["contact"]:
            score = 0.95
        elif a.contact and r["contact"] and r["contact"] not in a.contact:
            score = 0.5
        candidates.append({"id": r["id"], "company": r["company"],
                           "contact": r["contact"], "stage": r["stage"],
                           "confidence": score})
    con.close()
    bizlib.ok({"candidates": candidates,
               "hint": "confidence>=0.9: update it; 0.5-0.9: ask the user; none: create new."})


if __name__ == "__main__":
    main()
