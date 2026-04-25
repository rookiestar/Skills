#!/usr/bin/env python3
"""Generate full zh_en_core_supplement.json from Cambridge dictionary entries.

Reads all Cambridge entries, inverts their Chinese definitions into zh→en mappings,
then merges with the existing hand-curated supplement (which takes priority).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from scripts.dictionary_utils import parse_definitions  # noqa: E402

# Patterns to skip — sentence fragments, examples, noise
SKIP_RE = re.compile(
    r"^[\s\"\"''（）()【】\[\]…—~～]"  # starts with punctuation/brackets
    r"|^[a-zA-Z]"  # starts with Latin letter (likely example or English fragment)
    r"^[\d]"  # starts with number
    r".{20,}"  # too long (likely a full sentence)
    r"[）)]"  # contains stray closing paren (incomplete strip)
)

# Common Chinese particles to strip from term endings
PARTICLE_SUFFIXES = ("的", "了", "着", "过", "等", "们", "之", "性", "化")

MIN_ZH_LEN = 1
MAX_ZH_LEN = 10


def strip_particles(term: str) -> str:
    """Strip common particles from Chinese term endings for better matching."""
    while term.endswith(PARTICLE_SUFFIXES) and len(term) > 1:
        term = term[:-1]
    return term


def is_valid_zh_term(text: str) -> bool:
    """Check if a text fragment is a valid Chinese term for lookup."""
    if not text:
        return False
    n = len(text)
    if n < MIN_ZH_LEN or n > MAX_ZH_LEN:
        return False
    if SKIP_RE.match(text):
        return False
    chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
    if chinese_chars == 0:
        return False
    if chinese_chars < n * 0.5:
        return False
    return True


def split_definition(def_text: str) -> list[str]:
    """Split a single definition string into candidate Chinese terms."""
    terms: list[str] = []
    for raw in re.split(r"[;；,，、/|]", def_text):
        term = raw.strip()
        # Strip trailing punctuation
        term = term.rstrip("。．.,，;：:、）)】]")
        # Strip leading brackets/parens
        term = term.lstrip("（([【")
        # Strip particles for cleaner matching (抽象的 → 抽象)
        term_clean = strip_particles(term)
        # Use stripped version if valid, otherwise try original
        candidate = term_clean if term_clean else term
        if is_valid_zh_term(candidate):
            terms.append(candidate)
    return terms


def cam_pos_to_short(pos: str) -> str:
    """Convert Cambridge POS to short ECDICT-style notation."""
    if not pos:
        return ""
    p = pos.lower().strip()
    mapping = {
        "noun": "n.", "verb": "v.", "adjective": "a.", "adverb": "adv.",
        "preposition": "prep.", "pronoun": "pron.", "conjunction": "conj.",
        "interjection": "int.", "exclamation": "int.", "determiner": "det.",
        "auxiliary verb": "aux.", "modal verb": "mod.v.",
        "count noun": "n.", "uncount noun": "n.",
        "singular": "n.", "plural": "n.",
        "indefinite pronoun": "pron.", "relative pronoun": "pron.",
        "possessive": "det.", "article": "art.",
    }
    return mapping.get(p, pos)


def generate_from_cambridge(db_path: Path) -> dict[str, dict]:
    """Read Cambridge entries and build {zh_term: {"term", "entries"}} dict."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT word, pos, definitions FROM dictionary WHERE source = 'cambridge' AND definitions IS NOT NULL AND definitions != ''"
    ).fetchall()
    conn.close()

    result: dict[str, dict] = {}
    for row in rows:
        en_word = row["word"]
        if not en_word:
            continue
        pos_short = cam_pos_to_short(row["pos"] or "")
        definitions = parse_definitions(row["definitions"])

        for rank, def_text in enumerate(definitions):
            priority = max(100, 900 - rank * 100)  # 900, 800, 700, ...
            zh_terms = split_definition(def_text)
            for zh_term in zh_terms:
                if zh_term not in result:
                    result[zh_term] = {"term": zh_term, "entries": []}
                # Avoid duplicate en_word for same zh_term
                existing_words = {e["word"] for e in result[zh_term]["entries"]}
                if en_word not in existing_words:
                    result[zh_term]["entries"].append({
                        "word": en_word,
                        "pos": pos_short,
                        "priority": priority,
                    })

    return result


def load_hand_curated(supplement_path: Path) -> dict[str, dict]:
    """Load existing hand-curated supplement."""
    if not supplement_path.exists():
        return {}
    raw = json.loads(supplement_path.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for item in raw:
        term = item.get("term", "")
        if not term:
            continue
        # Boost hand-curated priorities to 1000+
        entries = []
        for i, entry in enumerate(item.get("entries", [])):
            e = dict(entry)
            e["priority"] = entry.get("priority", 0) + 1000  # ensure > auto-generated
            entries.append(e)
        result[term] = {"term": term, "entries": entries}
    return result


def merge(cam_dict: dict[str, dict], hand_dict: dict[str, dict]) -> list[dict]:
    """Merge Cambridge-generated with hand-curated. Hand-curated terms are never mixed with auto-generated."""
    merged = dict(hand_dict)  # start with hand-curated (complete, no additions)
    for zh_term, cam_entry in cam_dict.items():
        if zh_term not in merged:
            # No hand-curated version, use Cambridge as-is
            merged[zh_term] = cam_entry
        # else: term has hand-curated data — skip all Cambridge entries for this term

    # Sort each term's entries by priority desc
    for entry in merged.values():
        entry["entries"].sort(key=lambda e: e.get("priority", 0), reverse=True)

    return list(merged.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Build full curated zh_en_core supplement")
    parser.add_argument("--db", default=ROOT / "data" / "dictionary.db")
    parser.add_argument("--supplement", default=ROOT / "data" / "zh_en_hand_curated.json")
    parser.add_argument("--output", default=None, help="Output path (default: overwrite supplement)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    print("Generating from Cambridge entries...")
    cam_dict = generate_from_cambridge(db_path)
    print(f"  Cambridge-derived: {len(cam_dict)} Chinese terms")

    print("Loading hand-curated supplement...")
    hand_dict = load_hand_curated(Path(args.supplement))
    print(f"  Hand-curated: {len(hand_dict)} Chinese terms")

    print("Merging...")
    merged = merge(cam_dict, hand_dict)
    print(f"  Total: {len(merged)} Chinese terms")

    total_mappings = sum(len(e["entries"]) for e in merged)
    print(f"  Total mappings: {total_mappings}")

    if args.dry_run:
        # Stats
        hand_only = sum(1 for e in merged if any(x.get("priority", 0) >= 1000 for x in e["entries"]))
        cam_only = sum(1 for e in merged if all(x.get("priority", 0) < 1000 for x in e["entries"]))
        both = len(merged) - hand_only - cam_only
        print(f"\n--- Source breakdown ---")
        print(f"  Hand-curated only: {hand_only}")
        print(f"  Cambridge only:   {cam_only}")
        print(f'  Both (merged):    {both}')

        print(f"\n--- Sample output ---")
        for entry in merged[:15]:
            top = entry["entries"][0]
            more = f" +{len(entry['entries'])-1}" if len(entry["entries"]) > 1 else ""
            src = "✋" if top.get("priority", 0) >= 1000 else "  "
            print(f"  {src} {entry['term']:12s} => {top['word']:16s} [{top.get('pos','')}] {more}")
        return 0

    output_path = Path(args.output) if args.output else ROOT / "data" / "zh_en_core_supplement.json"
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nWritten to {output_path} ({output_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
