#!/usr/bin/env python3
"""Split dictionary.definitions JSON array into word_senses table (one row per sense)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def create_table(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS word_senses;
        CREATE TABLE word_senses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            pos TEXT DEFAULT '',
            definition TEXT NOT NULL,
            example TEXT DEFAULT '',
            sense_rank INTEGER DEFAULT 0,
            source TEXT DEFAULT 'cambridge',
            cefr_level TEXT DEFAULT NULL
        );
        CREATE INDEX idx_senses_word ON word_senses(word);
    """)
    conn.commit()


def migrate(conn: sqlite3.Connection) -> dict[str, int]:
    """Read dictionary table, split definitions into word_senses rows."""
    rows = conn.execute(
        "SELECT word, pos, definitions, example, source, cefr_level "
        "FROM dictionary WHERE definitions IS NOT NULL AND definitions != ''"
    ).fetchall()

    total_senses = 0
    total_words = 0
    for row in rows:
        word = row["word"]
        pos = row["pos"] or ""
        example = row["example"] or ""
        source = row["source"] or "cambridge"
        cefr_level = row["cefr_level"]

        definitions = []
        if isinstance(row["definitions"], str):
            try:
                definitions = json.loads(row["definitions"])
            except (json.JSONDecodeError, TypeError):
                definitions = []
        elif isinstance(row["definitions"], list):
            definitions = row["definitions"]

        if not definitions:
            continue

        total_words += 1
        for rank, def_text in enumerate(definitions):
            if not def_text or not str(def_text).strip():
                continue
            # First sense gets the original example
            sense_example = example if rank == 0 else ""
            conn.execute(
                "INSERT INTO word_senses (word, pos, definition, example, sense_rank, source, cefr_level) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (word, pos, str(def_text).strip(), sense_example, rank, source, cefr_level),
            )
            total_senses += 1

    conn.commit()
    return {"words": total_words, "senses": total_senses}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build word_senses table from dictionary")
    parser.add_argument("--db", default=ROOT / "data" / "dictionary.db")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        print("Creating word_senses table...")
        create_table(conn)

        print("Migrating senses from dictionary...")
        stats = migrate(conn)
        print(f"  {stats['words']} words → {stats['senses']} sense rows")

        # Verify
        total = conn.execute("SELECT COUNT(*) FROM word_senses").fetchone()[0]
        words = conn.execute("SELECT COUNT(DISTINCT word) FROM word_senses").fetchone()[0]
        avg = total / words if words else 0
        print(f"\nTable stats: {total} rows, {words} distinct words, {avg:.1f} senses/word")

        # Sample
        print("\n--- Sample ---")
        for w in ["variable", "happy", "run", "make", "get"]:
            senses = conn.execute(
                "SELECT pos, definition, example FROM word_senses WHERE word=? ORDER BY sense_rank",
                (w,),
            ).fetchall()
            print(f"\n  {w} ({len(senses)} senses):")
            for s in senses:
                ex = f"  💬 {s[2]}" if s[2] else ""
                print(f"    [{s[0]}] {s[1]}{ex}")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
