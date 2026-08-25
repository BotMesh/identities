#!/usr/bin/env python3
"""Initialize the ~/biz workspace and biz.db (idempotent)."""
import bizlib


def main():
    con = bizlib.connect()
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','virtual table') "
        "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'kb_fts_%'")]
    con.close()
    bizlib.ok({
        "biz_home": str(bizlib.BIZ_HOME),
        "db": str(bizlib.DB_PATH),
        "timezone": bizlib.TZ_NAME,
        "tables": sorted(tables),
    })


if __name__ == "__main__":
    main()
