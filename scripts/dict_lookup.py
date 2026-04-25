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
        return normalize_query(match.group(0))
    return normalize_query(text)


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


def load_word_senses(db_path: Path, word: str) -> list[dict[str, Any]]:
    """Load all senses for a word from word_senses + phonetic from dictionary."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "word_senses"):
            # Fallback: old single-row mode
            entry = load_sqlite_entry(db_path, word)
            if entry:
                defs = entry.get("definitions") or []
                return [{
                    "word": entry["word"],
                    "pos": entry.get("pos", ""),
                    "phonetic": entry.get("phonetic", ""),
                    "definition": d,
                    "example": entry.get("example", "") if i == 0 else "",
                } for i, d in enumerate(defs[:5]) if d]
            return []

        rows = conn.execute(
            """
            SELECT s.pos, s.definition, s.example, s.sense_rank,
                   d.phonetic, d.phonetic_uk, d.phonetic_us, d.word, d.source
            FROM word_senses s
            JOIN dictionary d ON s.word = d.word
            WHERE lower(d.word) = ?
            ORDER BY s.sense_rank ASC
            LIMIT 6
            """,
            (word.lower(),),
        ).fetchall()

        result: list[dict[str, Any]] = []
        phonetic = ""
        for row in rows:
            if not phonetic:
                pk = row["phonetic_uk"] or row["phonetic_us"] or row["phonetic"]
                phonetic = pk or ""
            result.append({
                "word": row["word"],
                "pos": row["pos"] or "",
                "phonetic": phonetic,
                "definition": row["definition"],
                "example": row["example"] or "",
                "source": row["source"] or "",
            })
        return result
    finally:
        conn.close()


def _upgrade_to_cambridge(conn: sqlite3.Connection, db_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """If a matched word has a Cambridge entry in the main table, use that instead.

    Preserves pos and _nuance from the curated zh_en_core entry since those
    are specifically chosen for the Chinese→English mapping context.
    """
    word = entry.get("word", "")
    if not word or entry.get("source") == "cambridge":
        return entry
    cam = load_sqlite_entry(db_path, word)
    if cam and cam.get("source") == "cambridge":
        cam_out = entry_for_output(cam)
        # Preserve curated POS — Cambridge may have a different sense's POS
        curated_pos = entry.get("pos", "")
        if curated_pos:
            cam_out["pos"] = curated_pos
        # Preserve nuance
        curated_nuance = entry.get("_nuance", "")
        if curated_nuance:
            cam_out["_nuance"] = curated_nuance
        return cam_out
    return entry


def _load_zh_en_core(conn: sqlite3.Connection, db_path: Path, query: str, limit: int, seen: set[str]) -> list[dict[str, Any]]:
    """Query the curated zh_en_core table. Pure curated mode — no fallback."""
    if not table_exists(conn, "zh_en_core"):
        return []
    rows = conn.execute(
        """
        SELECT en_word, pos, nuance
        FROM zh_en_core
        WHERE zh_term = ? AND source = 'curated'
        ORDER BY frequency DESC, sense_rank ASC
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        word = row["en_word"]
        if word in seen:
            continue
        seen.add(word)
        curated_pos = row["pos"] or ""
        curated_nuance = row["nuance"] or ""
        entry = load_sqlite_entry(db_path, word)
        if entry is None:
            entry = {
                "word": word,
                "pos": curated_pos,
                "phonetic": "",
                "definitions": [],
                "example": "",
                "source": "zh_en_core",
                "_nuance": curated_nuance,
            }
        else:
            # Preserve curated POS/nuance — Cambridge may have a different sense
            entry["pos"] = curated_pos
            entry["_nuance"] = curated_nuance
        entry = _upgrade_to_cambridge(conn, db_path, entry)
        results.append(entry_for_output(entry))
    return results


def load_sqlite_matches(db_path: Path, query: str, limit: int = 2) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        seen: set[str] = set()
        return _load_zh_en_core(conn, db_path, query, limit, seen)
    finally:
        conn.close()


def load_sample_entry(sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]], word: str) -> dict[str, Any] | None:
    by_word, _ = sample_indexes
    return by_word.get(word.lower())



def format_en_to_zh_text(result: dict[str, Any]) -> str:
    """Format en→zh result with one line per sense, each with own pos + definition + example."""
    word = result.get("word", "")
    senses = result.get("senses", [])

    # Backward compat: old single-entry format
    if not senses and "definitions" in result:
        senses = [{"pos": result.get("pos", ""), "definition": d, "example": result.get("example", "") if i == 0 else ""}
                 for i, d in enumerate((result.get("definitions") or [])[:3]) if d]

    if not senses:
        return f"**{word}**"

    lines = [f"**{word}**"]

    # Phonetic from first sense
    phonetic = senses[0].get("phonetic", "") or ""
    if phonetic:
        lines.append(f"- 🔤 音标：{phonetic}")

    for i, s in enumerate(senses[:5]):
        pos = s.get("pos", "") or ""
        definition = s.get("definition", "") or ""
        example = s.get("example", "") or ""

        if pos:
            lines.append(f"- 📖 {pos} {definition}")
        else:
            lines.append(f"- 📖 {definition}")

        if example:
            lines.append(f"  💬 {example}")

    return "\n".join(lines)


def format_zh_to_en_text(result: dict[str, Any]) -> str:
    query = result.get("query", "")
    matches = result.get("matches", [])
    lines = [f"**{query}**"]

    for i, m in enumerate(matches[:3]):
        w = m["word"]
        pos = m.get("pos") or ""
        phonetic = m.get("phonetic") or ""
        defs = m.get("definitions") or []
        example = m.get("example") or ""
        nuance = m.get("_nuance", "") or ""

        if i == 0:
            label = "🔤 最常用英文："
        elif i == 1:
            label = "🔤 第二常用英文："
        else:
            label = "🔤 其他表达："
        line = f"{label}{w}"
        if phonetic:
            line += f" {phonetic}"
        lines.append(f"- {line}")
        if i == 0 and pos:
            lines.append(f"- 📖 词性：{pos}")
        if nuance:
            lines.append(f"- 💡 辨析：{nuance}")
        trans = defs[0] if defs else ""
        if trans and not nuance:
            lines.append(f"- 🇨🇳 对应义：{trans}")
        if i == 0 and example:
            lines.append(f"- 💬 例句：{example}")

    return "\n".join(lines)


def append_missing_word(missing_log: Path, query: str) -> None:
    missing_log.parent.mkdir(parents=True, exist_ok=True)
    with missing_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{query}\n")


def lookup_en_to_zh(query: str, db_path: Path, sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    word = extract_en_query(query)
    senses = load_word_senses(db_path, word)
    if not senses:
        # Fallback for words without senses table
        entry = load_sqlite_entry(db_path, word)
        if entry is None:
            entry = load_sample_entry(sample_indexes, word)
        if entry is None:
            append_missing_word(db_path.parent / "missing_words.log", word)
            return {"error": "not_found", "mode": "en_to_zh", "query": word}
        return {"word": word, "senses": [entry_for_output(entry)]}
    return {"word": word, "senses": senses}


def lookup_zh_to_en(query: str, db_path: Path, sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    phrase = extract_zh_query(query)
    matches = load_sqlite_matches(db_path, phrase)
    if not matches:
        append_missing_word(db_path.parent / "missing_words.log", phrase)
        return {"error": "not_found", "mode": "zh_to_en", "query": phrase}
    return {"query": phrase, "matches": matches}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local dictionary lookup")
    parser.add_argument("--mode", required=True, choices=("en_to_zh", "zh_to_en"))
    parser.add_argument("--format", default="json", choices=("json", "text"), help="Output format (default: json)")
    parser.add_argument("query", help="Word or phrase to look up")
    parser.add_argument("--data-dir", default=None, help="Directory with dictionary assets")
    parser.add_argument("--db", default=None, help="Path to dictionary.db")
    parser.add_argument("--sample", default=None, help="Path to sample_dictionary.json")
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
        if args.format == "text":
            print(f"这个词我还没收录，稍后帮你加上 📚")
        else:
            print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 4

    if args.format == "text":
        if args.mode == "en_to_zh":
            print(format_en_to_zh_text(result))
        else:
            print(format_zh_to_en_text(result))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
