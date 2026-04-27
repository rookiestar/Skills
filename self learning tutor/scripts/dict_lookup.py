#!/usr/bin/env python3
"""Local dictionary lookup for self-learning-tutor."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dictionary_utils import (  # noqa: E402
    build_reverse_terms,
    normalize_query,
    normalize_zh_term,
    record_to_entry,
    strip_lookup_cues_en,
    strip_lookup_cues_zh,
)


def resolve_path(value: str | None, env_name: str, default: Path) -> Path:
    if value:
        return Path(value)
    env_value = os.environ.get(env_name)
    if env_value:
        return Path(env_value)
    return default


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def load_sample_indexes(sample_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if not sample_path.exists():
        return {}, {}

    raw = json.loads(sample_path.read_text(encoding="utf-8"))
    by_word: dict[str, dict[str, Any]] = {}
    by_zh: dict[str, list[dict[str, Any]]] = {}

    for item in raw:
        entry = record_to_entry(item)
        if not entry["word"]:
            continue
        by_word[entry["word"].lower()] = entry
        zh_terms = item.get("zh_terms") if isinstance(item, dict) else None
        terms = build_reverse_terms(entry["definitions"], zh_terms if isinstance(zh_terms, list) else None)
        if not terms:
            terms = entry["definitions"]
        for term in terms:
            by_zh.setdefault(normalize_zh_term(term), []).append(entry)

    return by_word, by_zh


def entry_for_output(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "word": entry["word"],
        "pos": entry["pos"],
        "phonetic": entry["phonetic"],
        "definitions": entry["definitions"],
        "example": entry["example"],
        "source": entry["source"],
    }


def extract_en_query(query: str) -> str:
    text = strip_lookup_cues_en(query)
    match = re.match(r"[A-Za-z][A-Za-z' -]*", text)
    if match:
        return normalize_query(match.group(0)).lower()
    return normalize_query(text).lower()


def extract_zh_query(query: str) -> str:
    text = strip_lookup_cues_zh(query)
    text = re.sub(r"[吗嘛呀啊呢哦吧哈！？。.？]+$", "", text).strip()
    return normalize_zh_term(text)


def load_sqlite_entry(db_path: Path, word: str) -> dict[str, Any] | None:
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "dictionary"):
            return None
        row = conn.execute(
            "SELECT * FROM dictionary WHERE lower(word) = ? OR word = ? LIMIT 1",
            (word.lower(), word),
        ).fetchone()
        if row is None:
            return None
        return record_to_entry(row)
    finally:
        conn.close()


def load_sqlite_matches(db_path: Path, query: str, limit: int = 2) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        matches: list[dict[str, Any]] = []
        if table_exists(conn, "dictionary_reverse"):
            rows = conn.execute(
                """
                SELECT zh_term, word, pos, phonetic, source, frequency, sense_rank
                FROM dictionary_reverse
                WHERE zh_term = ?
                ORDER BY CASE WHEN frequency > 0 THEN 0 ELSE 1 END, sense_rank ASC, frequency ASC, word ASC
                LIMIT ?
                """,
                (query, limit * 4),
            ).fetchall()
            if not rows:
                rows = conn.execute(
                    """
                SELECT zh_term, word, pos, phonetic, source, frequency, sense_rank
                FROM dictionary_reverse
                WHERE zh_term LIKE ? OR ? LIKE zh_term
                    ORDER BY CASE WHEN frequency > 0 THEN 0 ELSE 1 END, sense_rank ASC, frequency ASC, word ASC
                    LIMIT ?
                    """,
                    (f"%{query}%", query, limit * 4),
                ).fetchall()

            seen: set[str] = set()
            for row in rows:
                word = row["word"]
                if word in seen:
                    continue
                seen.add(word)
                entry = load_sqlite_entry(db_path, word)
                if entry is None:
                        entry = {
                            "word": word,
                            "pos": row["pos"] or "",
                            "phonetic": row["phonetic"] or "",
                            "definitions": [],
                            "example": "",
                            "source": row["source"] or "ecdict",
                        }
                matches.append(entry_for_output(entry))
                if len(matches) >= limit:
                    break
            if matches:
                return matches

        if table_exists(conn, "dictionary"):
            rows = conn.execute("SELECT word, definitions FROM dictionary LIMIT 500").fetchall()
            seen = set()
            for row in rows:
                entry = record_to_entry(row)
                if not entry["word"] or entry["word"] in seen:
                    continue
                candidates = build_reverse_terms(entry["definitions"], None)
                if any(query == candidate or query in candidate or candidate in query for candidate in candidates):
                    seen.add(entry["word"])
                    matches.append(entry_for_output(entry))
                    if len(matches) >= limit:
                        break
        return matches
    finally:
        conn.close()


def load_word_senses(db_path: Path, word: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "word_senses"):
            entry = load_sqlite_entry(db_path, word)
            if entry:
                defs = entry.get("definitions") or []
                raw_examples = entry.get("example", "")
                examples: list[str] = []
                if raw_examples:
                    try:
                        parsed = json.loads(raw_examples)
                        if isinstance(parsed, list):
                            examples = parsed
                        else:
                            examples = [str(parsed)] if str(parsed) else []
                    except (json.JSONDecodeError, TypeError):
                        examples = [raw_examples] if raw_examples else []
                return [{"word": entry["word"], "phonetic": entry.get("phonetic", ""), "definition": d, "example": examples[i] if i < len(examples) else ""} for i, d in enumerate(defs[:5]) if d]
            return []
        rows = conn.execute(
            "SELECT s.pos,s.definition,s.example,s.sense_rank,d.phonetic,d.phonetic_uk,d.phonetic_us,d.word,d.source FROM word_senses s JOIN dictionary d ON s.word=d.word WHERE lower(d.word)=? ORDER BY s.sense_rank ASC LIMIT 6",
            (word.lower(),),
        ).fetchall()
        result = []
        phonetic = ""
        for row in rows:
            if not phonetic:
                phonetic = row["phonetic_uk"] or row["phonetic_us"] or row["phonetic"] or ""
            result.append({"word": row["word"], "pos": row["pos"] or "", "phonetic": phonetic, "definition": row["definition"], "example": row["example"] or "", "source": row["source"] or ""})
        return result
    finally:
        conn.close()


def load_sample_entry(sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]], word: str) -> dict[str, Any] | None:
    by_word, _ = sample_indexes
    return by_word.get(word.lower())


def load_sample_matches(sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]], query: str, limit: int = 2) -> list[dict[str, Any]]:
    _, by_zh = sample_indexes
    matches = list(by_zh.get(query, []))
    if not matches:
        for term, entries in by_zh.items():
            if query in term or term in query:
                matches.extend(entries)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in sorted(matches, key=lambda item: (-item.get("frequency", 0), item["word"])):
        if entry["word"] in seen:
            continue
        seen.add(entry["word"])
        deduped.append(entry_for_output(entry))
        if len(deduped) >= limit:
            break
    return deduped


def append_missing_word(missing_log: Path, query: str) -> None:
    missing_log.parent.mkdir(parents=True, exist_ok=True)
    with missing_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{query}\n")


def format_en_to_zh_text(result: dict[str, Any]) -> str:
    word = result.get("word", "")
    senses = result.get("senses", [])

    if not senses and "definitions" in result:
        senses = [{"pos": result.get("pos", ""), "definition": d, "example": result.get("example", "") if i == 0 else ""} for i, d in enumerate((result.get("definitions") or [])[:3]) if d]

    if not senses:
        return f"**{word}**"

    parts = [f"**{word}**"]

    phonetic = senses[0].get("phonetic", "") or ""
    if phonetic:
        parts.append(f"\n🔤 {phonetic}\n")

    for i, s in enumerate(senses[:5]):
        definition = s.get("definition") or ""
        example = s.get("example") or ""

        num = f"{i + 1}. "
        parts.append(f"{num}{definition}")

        if example:
            parts.append(f"\t💬 {example}")

        if i < len(senses[:5]) - 1:
            parts.append("")

    return "\n".join(parts)


def lookup_en_to_zh(query: str, db_path: Path, sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    word = extract_en_query(query)
    senses = load_word_senses(db_path, word)
    if not senses:
        entry = load_sqlite_entry(db_path, word)
        if entry is None:
            entry = load_sample_entry(sample_indexes, word)
        if entry is None:
            append_missing_word(db_path.parent / "missing_words.log", word)
            return {"error": "not_found", "mode": "en_to_zh", "query": word}
        defs = entry.get("definitions") or []
        raw_examples = entry.get("example", "")
        examples: list[str] = []
        if raw_examples:
            try:
                parsed = json.loads(raw_examples)
                if isinstance(parsed, list):
                    examples = parsed
                else:
                    examples = [str(parsed)] if str(parsed) else []
            except (json.JSONDecodeError, TypeError):
                examples = [raw_examples] if raw_examples else []
        senses = [{"word": entry["word"], "phonetic": entry.get("phonetic", ""), "definition": d, "example": examples[i] if i < len(examples) else ""} for i, d in enumerate(defs[:5]) if d]
        return {"word": word, "senses": senses}
    return {"word": word, "senses": senses}


def lookup_zh_to_en(query: str, db_path: Path, sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    phrase = extract_zh_query(query)
    matches = load_sqlite_matches(db_path, phrase)
    if not matches:
        matches = load_sample_matches(sample_indexes, phrase)
    if not matches:
        append_missing_word(db_path.parent / "missing_words.log", phrase)
        return {"error": "not_found", "mode": "zh_to_en", "query": phrase}
    return {"query": phrase, "matches": matches}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local dictionary lookup")
    parser.add_argument("--mode", required=True, choices=("en_to_zh", "zh_to_en"))
    parser.add_argument("query", help="Word or phrase to look up")
    parser.add_argument("--data-dir", default=None, help="Directory with dictionary assets")
    parser.add_argument("--db", default=None, help="Path to dictionary.db")
    parser.add_argument("--sample", default=None, help="Path to sample_dictionary.json")
    parser.add_argument("--format", default="json", choices=("json", "text"), help="Output format")
    args = parser.parse_args()

    data_dir = resolve_path(args.data_dir, "SELF_LEARNING_TUTOR_DATA_DIR", ROOT / "data")
    db_path = resolve_path(args.db, "SELF_LEARNING_TUTOR_DB", data_dir / "dictionary.db")
    sample_path = resolve_path(args.sample, "SELF_LEARNING_TUTOR_SAMPLE", data_dir / "sample_dictionary.json")
    sample_indexes = load_sample_indexes(sample_path)

    if args.mode == "en_to_zh":
        result = lookup_en_to_zh(args.query, db_path, sample_indexes)
    else:
        result = lookup_zh_to_en(args.query, db_path, sample_indexes)

    if result.get("error") == "not_found":
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 4

    if args.format == "text" and args.mode == "en_to_zh":
        print(format_en_to_zh_text(result))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
