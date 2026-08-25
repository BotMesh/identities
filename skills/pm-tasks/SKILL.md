---
name: pm-tasks
description: Create tasks and track progress with daily digests
version: 1.0.0
metadata:
  hermes:
    tags: [tasks, project-management, business]
    category: business
---
# PM Tasks

Requires the `biz-core` conventions. Persistence follows biz-core `SCHEMA.md`.

## When to Use
- Creating projects/tasks ("set up a project and break it down"), changing
  status or due dates, listing what is due.
- The daily follow-up cron job.

## Procedure
1. All writes via `python scripts/task.py …` (add / status / due). Batch
   decomposition ("break it into 5 tasks") = multiple `add` calls, echoed as
   one combined receipt.
2. Status machine: `todo → doing → blocked → done` (any state → cancelled).
   `blocked` requires a `--note` blocker reason.
3. Daily digest (cron, weekdays 09:30): run `task.py report`, format the four
   sections (due today / overdue / stalled >3 days / blocked) grouped by
   project; if all are empty, send a single line ("No tasks due today").
4. When a `done` task has `from_lead`, append a timeline entry to that lead
   via crm-leads `upsert_lead.py --timeline`.

## Pitfalls
- Dates only from explicit input; resolve "Friday" to a concrete date and echo
  it back before writing.
- Never mark tasks done on assumption — only when the user says so.

## Verification
The script echoes the stored row; verify field-by-field before the receipt.
