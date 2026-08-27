# BotMesh Identities

> 中文用户指南：[USAGE.zh-CN.md](USAGE.zh-CN.md)

ClawUp identities (pre-configured skill bundles) and the business skills behind
them. An identity is selected when creating an agent on
[ClawUp](https://clawup.org); its skills are auto-installed into the agent's
workspace ([how identities work](https://docs.clawup.org/src/goat-metis-identity.md)).

## Identities

| Identity | Skills | For |
|---|---|---|
| [`digital-employee`](identities/digital-employee/) | biz-core · crm-leads · pm-tasks · my-calendar · flow-expense · xlsx (official) · skill-creator (official) | Full business assistant: voice leads, tasks, calendar, expenses |

**Register in ClawUp:** Settings → Identities → Create New Identity, then copy
the slug, name, description, and skill source list from the identity's
`identity.json`.

**Runtime note:** identity pre-seeding applies to the OpenClaw runtime. On the
Hermes Agent runtime, install the same skills manually:

```bash
hermes skills install github.com/BotMesh/identities/skills/biz-core
hermes skills install github.com/BotMesh/identities/skills/crm-leads
# ... and so on
```

## Skills in this repo

All five follow the [agentskills.io](https://agentskills.io/specification)
standard (`SKILL.md` + `scripts/` + `templates/` + `references/`) and need only
the Python standard library. Persistence is an explicit, shared contract —
one SQLite database plus a defined file tree, documented in
[skills/biz-core/SCHEMA.md](skills/biz-core/SCHEMA.md). Structured writes go
through `scripts/` (never LLM-edited files); high-risk fields (amounts, dates,
names) are never guessed.

| Skill | What it does |
|---|---|
| [biz-core](skills/biz-core/) | Shared SQLite data layer, IDs, receipt conventions ([SCHEMA.md](skills/biz-core/SCHEMA.md)) |
| [crm-leads](skills/crm-leads/) | Voice/text → structured lead KB with dedupe and timelines |
| [pm-tasks](skills/pm-tasks/) | Task CRUD + daily follow-up digest |
| [my-calendar](skills/my-calendar/) | Events, morning digest, reminder tick |
| [flow-expense](skills/flow-expense/) | Expense state machine, approval gate, append-only ledger + hledger-compatible double-entry journal with a `reconcile` check; also the template skeleton for new workflows |

## Curated ecosystem add-ons (reviewed 2026-08-25)

Best-of-breed skills reviewed from ClawHub, skills.sh, and
[awesome-hermes-agent](https://github.com/0xNyk/awesome-hermes-agent).
Not bundled by default — add per your setup, and check the trust boundary
before enabling any community skill.

| Add-on | Why | Caveat |
|---|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) `docx` / `pdf` | Quotes and proposals for leads | Official, widely trusted |
| [hermes-nextcloud](https://github.com/adnw-vinc/hermes-nextcloud) | CalDAV/CardDAV sync for self-hosted Nextcloud | MIT, beta |
| [hermes-telegram-checklist](https://github.com/johnsje183/hermes-telegram-checklist) | Native Telegram to-do checklists | MIT; needs an MTProto user session |
| [hermes-skill-kit](https://github.com/duruonanni/hermes-skill-kit) `feishu-response-format` | Feishu card/table formatting | **No license, 3★** — review before use |
| [hermes-skill-factory](https://github.com/Romanescu11/hermes-skill-factory) | Auto-generate skills from workflows | 536★ but no license; installer-based |
| [loremaster](https://github.com/loremaster-ai/loremaster) | Sprint-style PM pack | Experimental; heavier than SME needs |

Also built into Hermes: `/learn <dir|url>` converts any document set into a
knowledge-base skill — the fastest way to add a new KB.

## License

Code and skills in this repo: [MIT](LICENSE). External skills keep their own
licenses.
