#!/usr/bin/env python3
"""Migrate defined phrases from gaokao_phrases.json into dictionary.db.

Only inserts phrases that have non-empty definitions[].
Populates both 'dictionary' and 'dictionary_reverse' tables.
One-time migration — safe to re-run (INSERT OR IGNORE).

Usage:
    python3 scripts/migrate_phrases_to_db.py --db data/dictionary.db --phrases data/gaokao_phrases.json
    python3 scripts/migrate_phrases_to_db.py --db data/dictionary.db --phrases data/gaokao_phrases.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def migrate(db_path: Path, phrases_path: Path, dry_run: bool = False) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row

    # Ensure schema exists
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS dictionary (
            word TEXT PRIMARY KEY,
            phonetic TEXT,
            phonetic_uk TEXT,
            phonetic_us TEXT,
            definition TEXT,
            translation TEXT,
            definitions TEXT DEFAULT '[]',
            collins INTEGER DEFAULT 0,
            oxford INTEGER DEFAULT 0,
            tag TEXT,
            bnc INTEGER DEFAULT 0,
            frq INTEGER DEFAULT 0,
            frequency INTEGER DEFAULT 0,
            exchange TEXT,
            detail TEXT,
            audio TEXT,
            example TEXT,
            example_source TEXT,
            example_url TEXT,
            source TEXT DEFAULT 'cambridge',
            updated_at TEXT,
            cefr_level TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS dictionary_reverse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zh_term TEXT NOT NULL,
            word TEXT NOT NULL,
            pos TEXT,
            phonetic TEXT,
            source TEXT DEFAULT 'cambridge',
            frequency INTEGER DEFAULT 0,
            sense_rank INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_rev_zh ON dictionary_reverse(zh_term);
        CREATE INDEX IF NOT EXISTS idx_rev_word ON dictionary_reverse(word);
    """)

    data = json.loads(phrases_path.read_text("utf-8"))
    phrases = [p for p in data.get("phrases", []) if p.get("definitions")]

    inserted = 0
    skipped = 0
    reverse_inserted = 0
    existing = 0

    for entry in phrases:
        word = entry["phrase"]
        defs = entry.get("definitions", [])
        examples = entry.get("examples", [])
        freq = entry.get("frequency", 3)
        zh_terms = entry.get("zh_terms", [])

        # Check if already in dictionary (avoid duplicates)
        row = conn.execute(
            "SELECT 1 FROM dictionary WHERE word = ? AND source = 'gaokao_phrases'",
            (word,),
        ).fetchone()
        if row:
            existing += 1
            continue

        # Build example JSON
        ex_json = json.dumps(examples, ensure_ascii=False) if examples else "[]"

        # Build definitions JSON
        defs_json = json.dumps(defs, ensure_ascii=False)

        # Pick primary definition/translation for flat columns
        definition = defs[0] if defs else ""
        translation = ""
        for d in defs:
            chinese_chars = [c for c in d if "一" <= c <= "鿿"]
            if chinese_chars:
                translation = d
                break

        conn.execute(
            """INSERT OR IGNORE INTO dictionary
               (word, phonetic, definition, translation, definitions,
                example, source, frequency, updated_at)
               VALUES (?, '', ?, ?, ?, ?, 'gaokao_phrases', ?, datetime('now'))""",
            (word, definition, translation, defs_json, ex_json, freq),
        )
        if conn.total_changes > inserted:
            inserted += 1

        # Reverse index: zh_term → phrase
        seen_zh: set[str] = set()
        for rank, zh_term in enumerate(zh_terms[:5]):
            if zh_term in seen_zh:
                continue
            seen_zh.add(zh_term)
            conn.execute(
                """INSERT OR IGNORE INTO dictionary_reverse
                   (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                   VALUES (?, ?, 'phr.', '', 'gaokao_phrases', ?, ?)""",
                (zh_term, word, freq, rank),
            )
            if conn.total_changes > reverse_inserted + inserted:
                reverse_inserted += 1

        skipped += 1

    conn.commit()

    total_in_json = len(data.get("phrases", []))
    with_defs = sum(1 for p in data.get("phrases", []) if p.get("definitions"))
    result = {
        "total_phrases": total_in_json,
        "with_definitions": with_defs,
        "inserted": inserted,
        "already_existed": existing,
        "skipped_no_def": skipped - inserted - existing,
        "reverse_entries": reverse_inserted,
    }

    if dry_run:
        print(f"[DRY RUN] Would insert {inserted} phrases + {reverse_inserted} reverse entries")
    else:
        print(f"[Migrated] {result}")

    conn.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate phrases to dictionary.db")
    parser.add_argument("--db", required=True, help="Path to dictionary.db")
    parser.add_argument("--phrases", required=True, help="Path to gaokao_phrases.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    args = parser.parse_args()

    result = migrate(Path(args.db), Path(args.phrases), args.dry_run)
    print(f"\nDone: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
