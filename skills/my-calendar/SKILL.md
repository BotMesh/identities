---
name: my-calendar
description: Personal calendar with scheduled reminders
version: 1.0.0
metadata:
  hermes:
    tags: [calendar, reminders, business]
    category: business
---
# My Calendar

Requires the `biz-core` conventions. Persistence follows biz-core `SCHEMA.md`.

## When to Use
- Scheduling ("meet the client at 3pm tomorrow, remind me 30 minutes before"),
  one-off reminders ("remind me in half an hour"), agenda queries ("what's on
  next week").
- The two cron jobs: morning digest and reminder tick.

## Procedure
1. Add: resolve the time in the user's timezone (`BIZ_TZ`), echo the exact
   date/time back to confirm, then `python scripts/cal.py add --title …
   --at 2026-08-26T15:00 --remind 30`. One-off reminders are events with a
   "⏰ " title prefix.
2. If the script reports same-day events, mention potential clashes in the
   receipt.
3. Morning digest cron (daily 08:00): `cal.py digest` → today's events plus
   due tasks in one message.
4. Reminder cron (every 15 min): `cal.py tick` → send one reminder per fired
   event; if the list is empty, send NOTHING.

## Pitfalls
- Reminder precision is ±15 min (tick interval) — say so when the user sets a
  tight lead time; suggest ≥30 min for important meetings.
- Never silently move an event; changes require confirmation.

## Verification
`add` echoes the stored event; confirm date/time/lead-time against the user's
words before the receipt.
