#!/usr/bin/env python3
"""Expense workflow CLI (draft→submitted→approved→paid→archived).

Usage:
  expense.py add --date 2026-08-24 --amount 86.00 [--category taxi]
    [--reason "client visit"] [--lead L-...]
  expense.py attach --id X-... --file expenses/receipts/xxx.jpg
  expense.py move --id X-... --to submitted|approved|rejected|paid|archived
    [--by self] [--note "..."]
  expense.py list [--status draft] [--month 2026-08]
  expense.py report --month 2026-08     # monthly summary
  expense.py reconcile                  # approved-vs-paid balance check

Double-entry journal: `approved` and `paid` transitions also append an
hledger-compatible entry to expenses/journal.hledger, making "every approved
expense is paid exactly once" machine-checkable (the liabilities:reimbursable
account balances to zero). Writing the journal is pure stdlib; the optional
hledger binary is only used by `reconcile` for validation and balances.
"""
import argparse
import shutil
import subprocess
from decimal import Decimal

import bizlib

FLOW = {"draft": {"submitted"},
        "submitted": {"approved", "rejected"},
        "rejected": {"submitted"},
        "approved": {"paid"},
        "paid": {"archived"}}

JOURNAL = bizlib.BIZ_HOME / "expenses" / "journal.hledger"


def money(cents):
    return f"{Decimal(cents) / 100:.2f} CNY"


def journal_append(row, kind):
    """Append the double-entry posting for an approved/paid transition."""
    desc = " ".join((row["reason"] or "expense").split()) or "expense"
    reimb = f"liabilities:reimbursable:{row['approved_by'] or 'self'}"
    if kind == "approved":
        lines = [f"{row['date']} ({row['id']}) {desc}",
                 f"    expenses:{row['category'] or 'uncategorized'}    {money(row['amount_cents'])}",
                 f"    {reimb}"]
    else:  # paid
        lines = [f"{bizlib.now().strftime('%Y-%m-%d')} ({row['id']}) reimbursement payout",
                 f"    {reimb}    {money(row['amount_cents'])}",
                 "    assets:bank"]
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n")


def ledger_append(row, note=""):
    month = row["date"][:7]
    path = bizlib.BIZ_HOME / "expenses" / f"ledger-{month}.md"
    if not path.exists():
        path.write_text(f"# Ledger {month}\n\n> Append-only.\n\n", encoding="utf-8")
    amt = Decimal(row["amount_cents"]) / 100
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- {bizlib.iso()} · {row['id']} · ¥{amt} · {row['category'] or '-'}"
                f" · {row['status']} · {row['reason'] or ''} {note}\n")


def add(a, con):
    try:
        cents = int((Decimal(a.amount) * 100).to_integral_value())
    except Exception:
        bizlib.fail(f"invalid amount {a.amount!r}")
    xid = bizlib.seq_id(con, "X", "expenses", "%Y%m")
    ts = bizlib.iso()
    con.execute(
        "INSERT INTO expenses (id,date,amount_cents,category,reason,status,"
        " related_lead,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (xid, a.date, cents, a.category, a.reason, "draft", a.lead, ts, ts))
    con.commit()
    row = con.execute("SELECT * FROM expenses WHERE id=?", (xid,)).fetchone()
    ledger_append(row)
    bizlib.ok({"expense": dict(row), "amount_yuan": str(Decimal(cents) / 100)})


def attach(a, con):
    con.execute("UPDATE expenses SET receipt_file=?, updated_at=? WHERE id=?",
                (a.file, bizlib.iso(), a.id))
    con.commit()
    bizlib.ok({"expense": dict(con.execute(
        "SELECT * FROM expenses WHERE id=?", (a.id,)).fetchone())})


def move(a, con):
    r = con.execute("SELECT * FROM expenses WHERE id=?", (a.id,)).fetchone()
    if r is None:
        bizlib.fail(f"expense {a.id} not found")
    if a.to not in FLOW.get(r["status"], set()):
        bizlib.fail(f"illegal transition {r['status']} -> {a.to}")
    ts = bizlib.iso()
    ab, aat = (a.by or "self", ts) if a.to == "approved" else (r["approved_by"], r["approved_at"])
    con.execute("UPDATE expenses SET status=?, approved_by=?, approved_at=?,"
                " updated_at=? WHERE id=?", (a.to, ab, aat, ts, a.id))
    con.commit()
    row = con.execute("SELECT * FROM expenses WHERE id=?", (a.id,)).fetchone()
    ledger_append(row, note=(a.note or ""))
    out = {"expense": dict(row)}
    if a.to in ("approved", "paid"):
        journal_append(row, a.to)
        out["journal"] = str(JOURNAL)
    bizlib.ok(out)


def list_(a, con):
    q, args = "SELECT * FROM expenses WHERE 1=1", []
    if a.status:
        q += " AND status=?"; args.append(a.status)
    if a.month:
        q += " AND date LIKE ?"; args.append(a.month + "%")
    rows = con.execute(q + " ORDER BY date DESC", args).fetchall()
    bizlib.ok({"expenses": [dict(r) for r in rows]})


def report(a, con):
    rows = con.execute(
        "SELECT category, COUNT(*) n, SUM(amount_cents) cents FROM expenses"
        " WHERE date LIKE ? AND status IN ('approved','paid','archived')"
        " GROUP BY category ORDER BY cents DESC", (a.month + "%",)).fetchall()
    total = sum(r["cents"] or 0 for r in rows)
    bizlib.ok({"month": a.month,
               "by_category": [
                   {"category": r["category"], "count": r["n"],
                    "yuan": str(Decimal(r["cents"] or 0) / 100)} for r in rows],
               "total_yuan": str(Decimal(total) / 100)})


def reconcile(_a, con):
    """Check that every approved expense is paid exactly once."""
    out = {}
    rows = con.execute(
        "SELECT id, date, amount_cents, approved_by FROM expenses"
        " WHERE status='approved' ORDER BY date").fetchall()
    out["approved_awaiting_payment"] = [dict(r) for r in rows]
    out["awaiting_total_yuan"] = str(Decimal(sum(r["amount_cents"] for r in rows)) / 100)
    if not JOURNAL.exists():
        out["journal"] = "no journal yet (created on first approval)"
        bizlib.ok(out)
        return
    out["journal"] = str(JOURNAL)
    hledger = shutil.which("hledger")
    if not hledger:
        out["hledger"] = ("not installed — journal entries are still written; install the"
                          " single hledger binary (https://hledger.org) to enable"
                          " machine-checked validation and balances")
        bizlib.ok(out)
        return
    try:
        chk = subprocess.run([hledger, "-f", str(JOURNAL), "check"],
                             capture_output=True, text=True, timeout=30)
        bal = subprocess.run([hledger, "-f", str(JOURNAL), "balance",
                              "liabilities:reimbursable", "--no-total"],
                             capture_output=True, text=True, timeout=30)
        out["hledger_check"] = "ok" if chk.returncode == 0 else chk.stderr.strip()
        out["reimbursable_balance"] = (bal.stdout.strip()
                                       or "0 — every approved expense has been paid")
    except Exception as e:  # noqa: BLE001 — reconcile must never crash the receipt
        out["hledger_error"] = str(e)
    bizlib.ok(out)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("--date", required=True)
    s.add_argument("--amount", required=True); s.add_argument("--category")
    s.add_argument("--reason"); s.add_argument("--lead")
    s = sub.add_parser("attach"); s.add_argument("--id", required=True)
    s.add_argument("--file", required=True)
    s = sub.add_parser("move"); s.add_argument("--id", required=True)
    s.add_argument("--to", required=True); s.add_argument("--by"); s.add_argument("--note")
    s = sub.add_parser("list"); s.add_argument("--status"); s.add_argument("--month")
    s = sub.add_parser("report"); s.add_argument("--month", required=True)
    sub.add_parser("reconcile")
    a = p.parse_args()
    con = bizlib.connect()
    {"add": add, "attach": attach, "move": move, "list": list_,
     "report": report, "reconcile": reconcile}[a.cmd](a, con)
    con.close()


if __name__ == "__main__":
    main()
