# Persistence Scheme

The explicit, shared persistence contract for all business skills in this repo
(`biz-core`, `crm-leads`, `pm-tasks`, `my-calendar`, `flow-expense`). Every
skill reads and writes the same data layer; none invents its own storage.

## 1. Storage layout

```
$BIZ_HOME/                 # default ~/biz  (env BIZ_HOME)
  biz.db                   # SQLite — source of truth for ALL structured fields
  leads/
    INDEX.md               # generated view (render_index.py) — never hand-edit
    L-<company>-<contact>.md   # frontmatter mirror + narrative timeline
  tasks/                   # reserved for task narrative files
  calendar/                # reserved for rendered month views
  expenses/
    ledger-YYYY-MM.md      # append-only audit ledger (human-readable trail)
    journal.hledger        # append-only double-entry journal (hledger-compatible)
    receipts/              # receipt images referenced by expenses.receipt_file
```

## 2. Source-of-truth rules

| Data | Source of truth | Markdown role |
|---|---|---|
| Structured fields (stage, status, amounts, dates) | `biz.db` | mirror only, regenerable |
| Narrative (timelines, notes, blocker reasons) | lead/task `.md` files (append-only sections) | primary |
| Audit trail (expense history) | `ledger-*.md` (append-only) + `expenses` rows | both, ledger never rewritten |
| Money record (approved/paid postings) | `journal.hledger` (append-only, double-entry) | machine-checkable: `liabilities:reimbursable` balancing to zero proves every approved expense was paid exactly once |
| Search text | `kb_fts` (derived) | — |

Invariants:
- Writes go through skill `scripts/` only; the LLM never edits data files directly.
- Generated files (`INDEX.md`, rendered views) can be deleted and rebuilt at any time.
- Ledger files are append-only; corrections are new entries.
- Amounts are stored as integer cents; unknown numeric fields are `NULL`, never `0`.

## 3. Tables (schema version 1)

The authoritative DDL lives in `scripts/bizlib.py` (`DDL`); this section mirrors it.

- **leads** `(id PK, company NOT NULL, contact, title, stage CHECK new|contacted|qualified|proposal|won|lost, value_cny, next_action, next_due, source, created_at, updated_at)`
- **tasks** `(id PK, title NOT NULL, project, status CHECK todo|doing|blocked|done|cancelled, due, from_lead → leads.id, created_at, updated_at, done_at)`
- **events** `(id PK, title NOT NULL, starts_at NOT NULL, remind_before_min DEFAULT 30, reminded DEFAULT 0, location, related_lead → leads.id)`
- **expenses** `(id PK, date NOT NULL, amount_cents NOT NULL, category, reason, status CHECK draft|submitted|approved|rejected|paid|archived, receipt_file, related_lead → leads.id, approved_by, approved_at, created_at, updated_at)`
- **kb_fts** — FTS5 virtual table `(ref_id, kind, content)`, derived, rebuildable
- **meta** `(key PK, value)` — holds `schema_version`

## 4. ID formats

| Kind | Format | Example |
|---|---|---|
| Lead | `L-<company-slug>-<contact-slug>` | `L-acme-jane` |
| Task | `T-YYYYMMDD-NNN` | `T-20260825-001` |
| Event | `E-YYYYMMDD-NNN` | `E-20260825-001` |
| Expense | `X-YYYYMM-NNN` | `X-202608-001` |

Slugs keep CJK characters; IDs are stable once created.

## 5. Time

All timestamps are ISO-8601 with timezone offset, in the user's timezone
(env `BIZ_TZ`, default `Asia/Shanghai`). Dates (`due`, `next_due`, `date`)
are `YYYY-MM-DD`.

## 6. Versioning & migration policy

- `meta.schema_version` records the installed schema (currently `1`).
- Schema creation is idempotent (`CREATE ... IF NOT EXISTS`), so any skill can
  initialize the database and install order never matters.
- Breaking changes bump `SCHEMA_VERSION` in `bizlib.py` and must ship a
  migration path in `init_db.py` that upgrades in place (additive `ALTER TABLE`
  preferred; never destructive).
- Backup before migration: the whole scheme is two artifacts — `biz.db` plus
  the `$BIZ_HOME` file tree — so `tar` of `$BIZ_HOME` is a complete backup.
