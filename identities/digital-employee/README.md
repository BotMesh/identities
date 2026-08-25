# Digital Employee

The full business-assistant bundle: five custom business skills sharing one
SQLite data layer (`~/biz/biz.db`, see biz-core `SCHEMA.md`), plus two
best-in-class official skills.

| Skill | Role | Source |
|---|---|---|
| biz-core | Shared data layer & conventions | this repo |
| crm-leads | Voice → lead knowledge base | this repo |
| pm-tasks | Tasks & daily follow-up | this repo |
| my-calendar | Calendar & reminders | this repo |
| flow-expense | Expense workflow (copyable as a template for new workflows) | this repo |
| xlsx | Excel export for monthly reports | anthropics/skills (official) |
| skill-creator | Build new workflow/KB skills fast | anthropics/skills (official) |

**After creating the agent:**

1. Run `python skills/biz-core/scripts/init_db.py` once (idempotent).
2. Tell the agent who you are (name, timezone, expense confirmation threshold).
3. Create the cron jobs:
   - daily 08:00 — morning digest (`my-calendar` digest)
   - weekdays 09:30 — task follow-up (`pm-tasks` report)
   - every 15 min — reminder tick (`my-calendar` tick)
   - monthly, 1st, 09:00 — expense report (`flow-expense` report)
