#!/usr/bin/env python3
"""Import an ECDICT-style source into the local SQLite dictionary."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from itertools import islice
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dictionary_utils import build_reverse_terms, record_to_entry  # noqa: E402


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def detect_source_table(conn: sqlite3.Connection, preferred: str | None = None) -> str:
    candidates: list[str] = []
    if preferred:
        candidates.append(preferred)
    candidates.extend(["stardict", "ecdict", "dictionary"])

    for name in candidates:
        if table_exists(conn, name) and "word" in table_columns(conn, name):
            return name

    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        table_name = row[0]
        if table_name.startswith("sqlite_"):
            continue
        if "word" in table_columns(conn, table_name):
            return table_name

    raise RuntimeError("no source table with a word column found")


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA temp_store = MEMORY")


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS dictionary (
            word TEXT PRIMARY KEY,
            phonetic TEXT,
            phonetic_uk TEXT,
            phonetic_us TEXT,
            pos TEXT,
            definition TEXT,
            translation TEXT,
            definitions TEXT,
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
            source TEXT DEFAULT 'ecdict',
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS dictionary_reverse (
            zh_term TEXT NOT NULL,
            word TEXT NOT NULL,
            pos TEXT,
            phonetic TEXT,
            source TEXT DEFAULT 'ecdict',
            frequency INTEGER DEFAULT 0,
            sense_rank INTEGER DEFAULT 0,
            PRIMARY KEY (zh_term, word)
        );
        """
    )


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_dictionary_frq ON dictionary(frq);
        CREATE INDEX IF NOT EXISTS idx_dictionary_oxford ON dictionary(oxford);
        CREATE INDEX IF NOT EXISTS idx_dictionary_reverse_term ON dictionary_reverse(zh_term);
        """
    )


def read_json_source(source_path: Path) -> Iterator[dict[str, Any]]:
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("JSON source must be a list of entries")
    for item in raw:
        yield record_to_entry(item)


def read_csv_source(source_path: Path) -> Iterator[dict[str, Any]]:
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield record_to_entry(row)


def read_sqlite_source(source_conn: sqlite3.Connection, source_table: str) -> Iterator[dict[str, Any]]:
    source_conn.row_factory = sqlite3.Row
    rows = source_conn.execute(f"SELECT * FROM {source_table}")
    for row in rows:
        yield record_to_entry(row)


def iter_source_entries(source_path: Path, source_table: str | None = None) -> Iterator[dict[str, Any]]:
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        yield from read_json_source(source_path)
        return
    if suffix == ".csv":
        yield from read_csv_source(source_path)
        return

    conn = sqlite3.connect(str(source_path))
    try:
        table = detect_source_table(conn, source_table)
        yield from read_sqlite_source(conn, table)
    finally:
        conn.close()


def batch(iterable: Iterable[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            return
        yield chunk


def dictionary_row(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry["word"],
        entry["phonetic"],
        entry["phonetic_uk"],
        entry["phonetic_us"],
        entry["pos"],
        entry["definition"],
        entry["translation"],
        json.dumps(entry["definitions"], ensure_ascii=False),
        entry["collins"],
        entry["oxford"],
        entry["tag"],
        entry["bnc"],
        entry["frq"],
        entry["frequency"],
        entry["exchange"],
        entry["detail"],
        entry["audio"],
        entry["example"],
        entry["example_source"],
        entry["example_url"],
        entry["source"],
    )


def import_entries(entries: Iterable[dict[str, Any]], dest_path: Path, batch_size: int = 2000) -> tuple[int, int]:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()

    conn = sqlite3.connect(str(dest_path))
    try:
        configure_connection(conn)
        create_schema(conn)

        imported = 0
        reverse_rows = 0
        with conn:
            for chunk in batch(entries, batch_size):
                valid_entries = [entry for entry in chunk if entry["word"]]
                if not valid_entries:
                    continue

                conn.executemany(
                    """
                    INSERT OR REPLACE INTO dictionary (
                        word, phonetic, phonetic_uk, phonetic_us, pos,
                        definition, translation, definitions, collins, oxford,
                        tag, bnc, frq, frequency, exchange, detail, audio,
                        example, example_source, example_url, source, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, datetime('now')
                    )
                    """,
                    [dictionary_row(entry) for entry in valid_entries],
                )

                reverse_payload: list[tuple[Any, ...]] = []
                for entry in valid_entries:
                    for sense_rank, definition in enumerate(entry["definitions"], start=1):
                        terms = build_reverse_terms([definition], None)
                        for term in terms:
                            reverse_payload.append(
                                (
                                    term,
                                    entry["word"],
                                    entry["pos"],
                                    entry["phonetic"],
                                    entry["source"],
                                    entry["frequency"],
                                    sense_rank,
                                )
                            )
                    if not entry["definitions"] and entry.get("zh_terms"):
                        for sense_rank, definition in enumerate(entry["zh_terms"], start=1):
                            terms = build_reverse_terms([definition], None)
                            for term in terms:
                                reverse_payload.append(
                                    (
                                        term,
                                        entry["word"],
                                        entry["pos"],
                                        entry["phonetic"],
                                        entry["source"],
                                        entry["frequency"],
                                        sense_rank,
                                    )
                                )

                if reverse_payload:
                    conn.executemany(
                        """
                        INSERT OR REPLACE INTO dictionary_reverse (
                            zh_term, word, pos, phonetic, source, frequency, sense_rank
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        reverse_payload,
                    )
                    reverse_rows += len(reverse_payload)

                imported += len(valid_entries)

        create_indexes(conn)
        conn.commit()
        return imported, reverse_rows
    finally:
        conn.close()


def import_source(source_path: Path, dest_path: Path, source_table: str | None = None) -> tuple[int, int]:
    entries = iter_source_entries(source_path, source_table)
    return import_entries(entries, dest_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an ECDICT-style source into dictionary.db")
    parser.add_argument("--source", required=True, help="Path to the source CSV, SQLite, or JSON file")
    parser.add_argument("--dest", required=True, help="Path to the destination dictionary.db")
    parser.add_argument("--source-table", default=None, help="Optional source table name")
    args = parser.parse_args()

    source_path = Path(args.source)
    dest_path = Path(args.dest)
    imported, reverse_rows = import_source(source_path, dest_path, args.source_table)
    print(f"Imported {imported} entries and {reverse_rows} reverse rows into {dest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
