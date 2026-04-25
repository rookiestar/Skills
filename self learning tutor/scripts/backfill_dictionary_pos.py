#!/usr/bin/env python3
"""Backfill missing part-of-speech values in the dictionary database."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dictionary_utils import extract_pos_from_text  # noqa: E402


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def backfill_missing_pos(db_path: Path, table_name: str = "dictionary", dry_run: bool = False) -> tuple[int, int]:
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        columns = table_columns(conn, table_name)
        required = {"pos", "definition", "translation"}
        missing = sorted(required - columns)
        if missing:
            raise ValueError(f"table {table_name!r} is missing columns: {', '.join(missing)}")

        cursor = conn.execute(
            f"""
            SELECT rowid, pos, definition, translation
            FROM {table_name}
            WHERE COALESCE(TRIM(pos), '') = ''
            """
        )

        inspected = 0
        updated = 0
        for row in cursor:
            inspected += 1
            inferred = extract_pos_from_text(row["definition"]) or extract_pos_from_text(row["translation"])
            if not inferred:
                continue
            updated += 1
            if not dry_run:
                conn.execute(
                    f"UPDATE {table_name} SET pos = ? WHERE rowid = ?",
                    (inferred, row["rowid"]),
                )
                if updated % 2000 == 0:
                    conn.commit()

        if not dry_run:
            conn.commit()
        return inspected, updated
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing POS values in dictionary.db")
    parser.add_argument("--db", required=True, help="Path to dictionary.db")
    parser.add_argument("--table", default="dictionary", help="Table to update")
    parser.add_argument("--dry-run", action="store_true", help="Count updates without writing")
    args = parser.parse_args()

    inspected, updated = backfill_missing_pos(Path(args.db), table_name=args.table, dry_run=args.dry_run)
    mode = "dry-run" if args.dry_run else "updated"
    print(f"{mode}: inspected={inspected} updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
