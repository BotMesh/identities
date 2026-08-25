"""Shared data layer for BotMesh business skills.

Every skill ships its own copy of this file so each skill can be installed
standalone; schema creation is idempotent, so install order never matters.

Env:
  BIZ_HOME  data root, default ~/biz
  BIZ_TZ    IANA timezone, default Asia/Shanghai
"""
import os
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # py<3.9 fallback
    ZoneInfo = None

BIZ_HOME = Path(os.environ.get("BIZ_HOME", os.path.expanduser("~/biz")))
DB_PATH = BIZ_HOME / "biz.db"
TZ_NAME = os.environ.get("BIZ_TZ", "Asia/Shanghai")

DDL = """
CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  contact TEXT, title TEXT,
  stage TEXT NOT NULL DEFAULT 'new'
    CHECK (stage IN ('new','contacted','qualified','proposal','won','lost')),
  value_cny INTEGER,
  next_action TEXT, next_due TEXT, source TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL, project TEXT,
  status TEXT NOT NULL DEFAULT 'todo'
    CHECK (status IN ('todo','doing','blocked','done','cancelled')),
  due TEXT, from_lead TEXT REFERENCES leads(id),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, done_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL, starts_at TEXT NOT NULL,
  remind_before_min INTEGER NOT NULL DEFAULT 30,
  reminded INTEGER NOT NULL DEFAULT 0,
  location TEXT, related_lead TEXT REFERENCES leads(id)
);
CREATE TABLE IF NOT EXISTS expenses (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL, amount_cents INTEGER NOT NULL,
  category TEXT, reason TEXT,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','submitted','approved','rejected','paid','archived')),
  receipt_file TEXT, related_lead TEXT REFERENCES leads(id),
  approved_by TEXT, approved_at TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(ref_id, kind, content);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

SCHEMA_VERSION = "1"


def now():
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo(TZ_NAME))
    return datetime.now()


def iso(dt=None):
    return (dt or now()).isoformat(timespec="seconds")


def connect():
    """Open biz.db, creating directories and schema if needed (idempotent)."""
    for d in ("leads", "tasks", "calendar", "expenses/receipts"):
        (BIZ_HOME / d).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    con.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,))
    con.commit()
    return con


def slugify(s):
    s = unicodedata.normalize("NFKC", (s or "").strip().lower())
    s = re.sub(r"[^\w一-鿿]+", "-", s).strip("-")
    return s or "na"


def seq_id(con, prefix, table, date_fmt):
    """Sequential id like T-20260825-001 (prefix-date-NNN)."""
    stamp = now().strftime(date_fmt)
    like = f"{prefix}-{stamp}-%"
    n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE id LIKE ?", (like,)).fetchone()[0]
    return f"{prefix}-{stamp}-{n + 1:03d}"


def lead_id(company, contact):
    return f"L-{slugify(company)}-{slugify(contact)}"


def fts_upsert(con, ref_id, kind, content):
    con.execute("DELETE FROM kb_fts WHERE ref_id = ? AND kind = ?", (ref_id, kind))
    con.execute("INSERT INTO kb_fts (ref_id, kind, content) VALUES (?,?,?)",
                (ref_id, kind, content))


def fail(msg):
    """Structured error for the agent to relay to the user."""
    import json
    import sys
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def ok(payload):
    import json
    payload = {"ok": True, **payload}
    print(json.dumps(payload, ensure_ascii=False, default=str))
    return payload
