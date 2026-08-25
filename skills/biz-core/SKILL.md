---
name: biz-core
description: Shared data layer and conventions for business skills
version: 1.0.0
metadata:
  hermes:
    tags: [business, core, database]
    category: business
    config:
      - key: biz.home
        description: "Data root (env BIZ_HOME)"
        default: "~/biz"
      - key: biz.tz
        description: "IANA timezone (env BIZ_TZ)"
        default: "Asia/Shanghai"
---
# Biz Core

Foundation for `crm-leads`, `pm-tasks`, `my-calendar`, and `flow-expense`.

## When to Use
- First run of any business skill: run `scripts/init_db.py` once.
- When INDEX files look stale: run `scripts/render_index.py` to rebuild.

## Procedure
1. Data lives under `~/biz/` (env `BIZ_HOME`): SQLite `biz.db` is the source of
   truth for structured fields; markdown files carry narrative content
   (timelines, notes).
2. IDs: leads `L-<company>-<contact>`, tasks `T-YYYYMMDD-NNN`,
   events `E-YYYYMMDD-NNN`, expenses `X-YYYYMM-NNN`.
3. All timestamps are ISO-8601 in the user's timezone (`BIZ_TZ`). Resolve
   phrases like "tomorrow 3pm" in that timezone, then echo the exact date back
   for confirmation.
4. Every write ends with the three-part receipt in `templates/receipt.md`.

## Pitfalls
- NEVER edit files under `~/biz/` or `biz.db` directly — all writes go through
  each skill's `scripts/`.
- High-risk fields (amount, date, person, company) are never guessed: only
  store values stated explicitly; otherwise leave empty and ask.
- INDEX.md files are generated artifacts — never hand-edit.

## Verification
After any write, re-read the affected DB row and confirm field-by-field before
sending the receipt.
