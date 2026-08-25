---
name: flow-expense
description: Expense workflow with an approval gate and double-entry journal
version: 1.1.0
metadata:
  hermes:
    tags: [expense, workflow, approval, business]
    category: business
    config:
      - key: expense.confirm_threshold_cny
        description: "Second confirmation above this amount (yuan)"
        default: "500"
---
# Expense Flow

Requires `biz-core`. Persistence follows biz-core `SCHEMA.md`. This skill is
also the reference template for new workflows — copy its skeleton to add e.g.
leave requests.

## When to Use
- "Expense the taxi, 86 yuan" style requests; receipt photos sent right after;
  the monthly report cron.

## Procedure
1. Capture: `python scripts/expense.py add --date … --amount … [--category …]
   [--reason …] [--lead …]` → creates a `draft`. The amount must be explicit
   (never inferred); dates like "yesterday" are resolved and echoed back.
2. Receipt photo arriving next: save under `~/biz/expenses/receipts/`, then
   `expense.py attach --id … --file …`.
3. Approval gate: amount < threshold (config, default ¥500) → the user's
   receipt confirmation moves it `submitted → approved --by self`. Amount ≥
   threshold → send a SEPARATE confirmation message and wait for an explicit
   yes.
4. State machine `draft→submitted→approved/rejected→paid→archived`; illegal
   transitions are refused by the script.
5. Double-entry journal: `approved` and `paid` transitions automatically append
   hledger-compatible postings to `expenses/journal.hledger`
   (approved: `expenses:<category> / liabilities:reimbursable:<who>`;
   paid: `liabilities:reimbursable:<who> / assets:bank`). Writing needs no
   external tools; the optional hledger binary powers `reconcile`.
6. Reconciliation (run monthly, or when the user asks "is everything paid?"):
   `expense.py reconcile` lists approved-awaiting-payment items and, when
   hledger is installed, validates the journal and shows the
   `liabilities:reimbursable` balance — zero means every approved expense was
   paid exactly once.
7. Monthly cron (1st, 09:00): `expense.py report --month YYYY-MM` → send the
   summary; run `reconcile`; move paid items to archived.

## Adding a new workflow
Copy this skill directory, then redefine: the state machine, required fields,
the approval threshold, the ledger file, and the monthly report — every new
workflow MUST declare all five.

## Pitfalls
- Ledger and journal files are append-only: never rewrite history; corrections
  are new entries (a rejected-after-approved fix is a reversing posting).
- Never approve on the user's behalf without the confirmation required by the
  gate.
- Report figures come from re-runnable queries (`report` / hledger), never from
  model arithmetic.

## Verification
The script echoes the stored row after every step; verify the amount (in yuan)
and status before the receipt.
