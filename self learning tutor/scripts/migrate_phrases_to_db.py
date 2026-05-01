#!/usr/bin/env python3
"""Migrate defined phrases from gaokao_phrases.json into dictionary.db.

Only processes phrases that have non-empty definitions[].
Populates both 'dictionary' and 'dictionary_reverse' tables.
Re-runnable migration: refreshes existing gaokao phrase rows and any existing
rows that still have empty definitions.

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


def _has_nonempty_json_list(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text or text == "[]":
        return False
    try:
        parsed = json.loads(text)
    except Exception:
        return True
    return isinstance(parsed, list) and any(str(item).strip() for item in parsed)


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
            translation TEXT,
            definitions TEXT DEFAULT '[]',
            idioms TEXT DEFAULT '[]',
            collocations TEXT DEFAULT '[]',
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
    phrases = [p for p in data.get("phrases", []) if any(str(d).strip() for d in p.get("definitions", []))]

    inserted = 0
    refreshed = 0
    reverse_inserted = 0
    existing = 0

    for entry in phrases:
        word = entry["phrase"]
        defs = entry.get("definitions", [])
        examples = entry.get("examples", [])
        freq = entry.get("frequency", 3)
        zh_terms = entry.get("zh_terms", [])

        # Refresh rows that are already from gaokao_phrases, or legacy rows
        # that still have empty definitions for this phrase.
        row = conn.execute(
            "SELECT source, definitions FROM dictionary WHERE word = ? LIMIT 1",
            (word,),
        ).fetchone()
        if row:
            if row["source"] != "gaokao_phrases" and _has_nonempty_json_list(row["definitions"]):
                existing += 1
                continue
            refreshed += 1

        # Build example JSON
        ex_json = json.dumps(examples, ensure_ascii=False) if examples else "[]"

        # Build definitions JSON
        defs_json = json.dumps(defs, ensure_ascii=False)
        translation = ""
        for d in defs:
            chinese_chars = [c for c in d if "一" <= c <= "鿿"]
            if chinese_chars:
                translation = d
                break

        if not dry_run:
            if row:
                conn.execute(
                    """UPDATE dictionary
                       SET phonetic = '',
                           translation = ?,
                           definitions = ?,
                           example = ?,
                           source = 'gaokao_phrases',
                           frequency = ?,
                           updated_at = datetime('now')
                       WHERE word = ?""",
                    (translation, defs_json, ex_json, freq, word),
                )
            else:
                conn.execute(
                    """INSERT INTO dictionary
                       (word, phonetic, translation, definitions,
                        example, source, frequency, updated_at)
                       VALUES (?, '', ?, ?, ?, 'gaokao_phrases', ?, datetime('now'))""",
                    (word, translation, defs_json, ex_json, freq),
                )
        inserted += 1

        # Reverse index: zh_term → phrase
        if not dry_run:
            conn.execute(
                "DELETE FROM dictionary_reverse WHERE word = ?",
                (word,),
            )
        seen_zh: set[str] = set()
        for rank, zh_term in enumerate(zh_terms[:5]):
            if zh_term in seen_zh:
                continue
            seen_zh.add(zh_term)
            if not dry_run:
                conn.execute(
                    "INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank) VALUES (?, ?, 'phr.', '', 'gaokao_phrases', ?, ?)",
                    (zh_term, word, freq, rank),
                )
            reverse_inserted += 1

    if not dry_run:
        conn.commit()

    total_in_json = len(data.get("phrases", []))
    with_defs = sum(1 for p in data.get("phrases", []) if any(str(d).strip() for d in p.get("definitions", [])))
    result = {
        "total_phrases": total_in_json,
        "with_definitions": with_defs,
        "inserted": inserted,
        "refreshed": refreshed,
        "already_existed": existing,
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
