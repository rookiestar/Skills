#!/usr/bin/env python3
"""Build zh→en core index by inverting Cambridge definitions + hand-curated supplement."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from scripts.dictionary_utils import (  # noqa: E402
    build_reverse_terms,
    normalize_zh_term,
    parse_definitions,
    record_to_entry,
)

# Patterns to skip — sentence fragments, examples, noise
SKIP_PATTERNS = re.compile(
    r"^[\s\"\"''（）()【】\[\]…—~～]|"
    r"^[a-zA-Z]|"  # starts with Latin letter (likely example)
    r"^[\d]|"  # starts with number
    r".{30,}"  # too long (likely a sentence)
)

# Minimum length for a useful Chinese term
MIN_ZH_LEN = 1
MAX_ZH_LEN = 12


def extract_zh_terms_from_definition(def_text: str) -> list[str]:
    """Split a single definition string into individual Chinese terms."""
    terms: list[str] = []
    # Split on common delimiters
    for raw in re.split(r"[;；，,、/|]", def_text):
        term = normalize_zh_term(raw.strip())
        if not term:
            continue
        if len(term) < MIN_ZH_LEN or len(term) > MAX_ZH_LEN:
            continue
        if SKIP_PATTERNS.match(term):
            continue
        # Skip if it's mostly non-Chinese
        chinese_chars = sum(1 for c in term if "一" <= c <= "鿿")
        if chinese_chars == 0:
            continue
        if chinese_chars < len(term) * 0.5:
            continue
        terms.append(term)
    return terms


def build_cambridge_reverse(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Invert Cambridge entries: Chinese terms → English words."""
    rows = conn.execute(
        "SELECT word, pos, definitions FROM dictionary WHERE source = 'cambridge' AND definitions IS NOT NULL AND definitions != ''"
    ).fetchall()

    mappings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()  # (zh_term, en_word)

    for row in rows:
        en_word = row[0]
        pos = row[1] or ""
        defs_raw = row[2]

        definitions = parse_definitions(defs_raw)
        for rank, def_text in enumerate(definitions):
            zh_terms = extract_zh_terms_from_definition(def_text)
            for zh_term in zh_terms:
                key = (zh_term, en_word.lower())
                if key in seen:
                    continue
                seen.add(key)
                mappings.append({
                    "zh_term": zh_term,
                    "en_word": en_word,
                    "pos": pos,
                    "source": "cambridge_inverted",
                    "sense_rank": rank,
                    "frequency": 0,
                })

    return mappings


def load_supplement(supplement_path: Path) -> list[dict[str, Any]]:
    """Load hand-curated zh→en supplement JSON."""
    if not supplement_path.exists():
        return []

    raw = json.loads(supplement_path.read_text(encoding="utf-8"))
    supplements: list[dict[str, Any]] = []
    for item in raw:
        zh_term = item.get("term", "")
        entries = item.get("entries", [])
        for i, entry in enumerate(entries):
            en_word = entry.get("word", "")
            if not en_word or not zh_term:
                continue
            supplements.append({
                "zh_term": zh_term,
                "en_word": en_word,
                "pos": entry.get("pos", ""),
                "source": "curated",
                "sense_rank": i,
                "frequency": entry.get("priority", 1000 - i),  # higher = more important
                "nuance": entry.get("nuance", ""),
            })
    return supplements


def create_table(conn: sqlite3.Connection) -> None:
    """Create the zh_en_core table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS zh_en_core (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zh_term TEXT NOT NULL,
            en_word TEXT NOT NULL,
            pos TEXT DEFAULT '',
            source TEXT DEFAULT '',
            sense_rank INTEGER DEFAULT 0,
            frequency INTEGER DEFAULT 0,
            nuance TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_zh_en_core_term ON zh_en_core(zh_term)
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_zh_en_core_unique
        ON zh_en_core(zh_term, en_word)
    """)
    conn.commit()


def insert_mappings(conn: sqlite3.Connection, mappings: list[dict[str, Any]]) -> int:
    """Bulk insert mappings, skipping duplicates."""
    inserted = 0
    for m in mappings:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO zh_en_core (zh_term, en_word, pos, source, sense_rank, frequency, nuance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (m["zh_term"], m["en_word"], m["pos"], m["source"],
                 m["sense_rank"], m["frequency"], m.get("nuance", "")),
            )
            if conn.total_changes > inserted:
                inserted = conn.total_changes
        except sqlite3.Error:
            continue
    conn.commit()
    return conn.total_changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Build zh→en core index")
    parser.add_argument("--db", default=ROOT / "data" / "dictionary.db", help="Path to dictionary.db")
    parser.add_argument("--supplement", default=ROOT / "data" / "zh_en_core_supplement.json",
                        help="Path to hand-curated supplement")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))

    # Build Cambridge inverted index
    print("Building Cambridge inverted index...")
    cam_mappings = build_cambridge_reverse(conn)
    print(f"  Cambridge mappings: {len(cam_mappings)}")

    # Load supplement
    supp_mappings = load_supplement(Path(args.supplement))
    print(f"  Supplement mappings: {len(supp_mappings)}")

    # Supplement FIRST so curated entries win the unique (zh_term, en_word) key
    # Then Cambridge inverted fills in gaps
    all_mappings = supp_mappings + cam_mappings
    print(f"  Total mappings: {len(all_mappings)}")

    if args.dry_run:
        # Print sample
        print("\n--- Sample mappings ---")
        for m in all_mappings[:30]:
            nuance = f" ({m['nuance']})" if m.get("nuance") else ""
            print(f"  {m['zh_term']:12s} => {m['en_word']:16s} [{m['pos']}: rank={m['sense_rank']}]{nuance}")

        # Stats by source
        from collections import Counter
        sources = Counter(m["source"] for m in all_mappings)
        print(f"\n--- By source ---")
        for src, cnt in sources.most_common():
            print(f"  {src}: {cnt}")

        unique_terms = set(m["zh_term"] for m in all_mappings)
        unique_words = set((m["zh_term"], m["en_word"]) for m in all_mappings)
        print(f"\n  Unique Chinese terms: {len(unique_terms)}")
        print(f"  Unique (zh, en) pairs: {len(unique_words)}")
        return 0

    # Write to database
    create_table(conn)
    total = insert_mappings(conn, all_mappings)
    print(f"\nInserted {total} rows into zh_en_core")

    # Verify
    count = conn.execute("SELECT COUNT(*) FROM zh_en_core").fetchone()[0]
    terms = conn.execute("SELECT COUNT(DISTINCT zh_term) FROM zh_en_core").fetchone()[0]
    print(f"Table stats: {count} rows, {terms} distinct Chinese terms")

    # Quick test
    test_terms = ["餐厅", "看", "说", "大", "学习", "老师", "学生", "开心"]
    print("\n--- Quick lookup test ---")
    for t in test_terms:
        rows = conn.execute(
            "SELECT en_word, pos, source, sense_rank FROM zh_en_core WHERE zh_term = ? ORDER BY frequency DESC, sense_rank ASC LIMIT 3",
            (t,),
        ).fetchall()
        if rows:
            words = ", ".join(f"{r[0]}({r[2][:8]})" for r in rows)
            print(f"  {t}: {words}")
        else:
            print(f"  {t}: (not found)")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
