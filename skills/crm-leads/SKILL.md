---
name: crm-leads
description: Voice/text lead capture into a CRM knowledge base
version: 1.0.0
metadata:
  hermes:
    tags: [crm, leads, voice, business]
    category: business
    config:
      - key: crm.currency
        description: "Default currency"
        default: "CNY"
---
# CRM Leads

Requires the `biz-core` conventions (install it alongside this skill).
Persistence follows the shared contract in biz-core `SCHEMA.md`.

## When to Use
- The user dictates or types information about a customer contact, visit, or
  progress update.
- The user asks about a lead's status, or for lists/stats of leads.

## Procedure
1. First use: run biz-core `scripts/init_db.py` (idempotent — safe to rerun).
2. Capture:
   a. Extract fields from the (transcribed) text — see `references/fields.md`
      for the field/risk table.
   b. High-risk fields (company, person, amount, date) must appear explicitly
      in the input; vague phrases ("around 400k", "next week-ish") → leave
      empty and ask in the receipt.
   c. Dedupe first: `python scripts/find_lead.py --company X [--contact Y]`.
      Confidence ≥0.9 → update; 0.5–0.9 → ask the user; none → create.
   d. Write via `python scripts/upsert_lead.py …` (never edit files directly).
      Pass `--timeline "…"` to append the narrative entry.
   e. If a next_action was captured, run `python scripts/link_task.py
      --lead <id>` to create the follow-up task.
   f. Reply with the biz-core receipt; for voice input, quote the transcript
      at the end for correction.
3. Query: exact stats via `python scripts/query.py …` (SQL); fuzzy recall via
   `--fts`, then the platform's session search as fallback.

## Pitfalls
- Never edit `~/biz/` files or `biz.db` directly; scripts only.
- Never guess amounts or dates; resolve relative dates ("next Wednesday" →
  2026-09-02) and echo them back for confirmation before writing.
- Same company + same contact name → dedupe before creating.
- `leads/INDEX.md` is generated — never hand-edit.

## Verification
After upsert, the script echoes the stored row — compare it field-by-field
with what the user said before sending the receipt; on mismatch, correct via
another upsert (do not hand-edit files).
