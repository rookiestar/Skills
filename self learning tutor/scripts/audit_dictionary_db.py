#!/usr/bin/env python3
"""Audit completeness of dictionary.db.

Reports entries whose `definitions` are empty but `example` and/or `idioms`
still contain data. These are the records most likely to have lost their
actual definition payload during import.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
import re
from pathlib import Path


def _nonempty_json_list(value: object) -> bool:
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


CEFR_RE = re.compile(r"^[ABC][12]$")
TIMESTAMP_RE = re.compile(r"^20\d\d-\d\d-\d\d ")


def audit(db_path: Path, limit: int = 200) -> int:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT word, source, definitions, example, idioms, collocations, frequency, cefr_level FROM dictionary"
        ).fetchall()

        findings: dict[str, list[sqlite3.Row]] = defaultdict(list)
        counts = Counter()
        subset_cefr_counts = Counter()
        subset_cefr_samples: list[tuple[str, str]] = []
        all_cefr_counts = Counter()
        all_cefr_samples: list[tuple[str, str]] = []

        for row in rows:
            cefr = (row["cefr_level"] or "").strip()
            if not cefr:
                all_cefr_counts["empty"] += 1
            elif CEFR_RE.fullmatch(cefr):
                all_cefr_counts["valid"] += 1
            elif TIMESTAMP_RE.match(cefr):
                all_cefr_counts["timestamp_like"] += 1
                if len(all_cefr_samples) < 20:
                    all_cefr_samples.append((row["word"], cefr))
            else:
                all_cefr_counts["other_invalid"] += 1
                if len(all_cefr_samples) < 20:
                    all_cefr_samples.append((row["word"], cefr))

            has_defs = _nonempty_json_list(row["definitions"])
            has_example = _nonempty_json_list(row["example"])
            has_idioms = _nonempty_json_list(row["idioms"])
            has_collocations = _nonempty_json_list(row["collocations"])
            if has_defs:
                continue
            if has_example and has_idioms:
                tier = "high"
            elif has_example or has_idioms:
                tier = "medium"
            elif has_collocations:
                tier = "low"
            else:
                tier = None
            if tier:
                counts[tier] += 1
                findings[tier].append(row)

            if not cefr:
                subset_cefr_counts["empty"] += 1
            elif CEFR_RE.fullmatch(cefr):
                subset_cefr_counts["valid"] += 1
            elif TIMESTAMP_RE.match(cefr):
                subset_cefr_counts["timestamp_like"] += 1
                if len(subset_cefr_samples) < 20:
                    subset_cefr_samples.append((row["word"], cefr))
            else:
                subset_cefr_counts["other_invalid"] += 1
                if len(subset_cefr_samples) < 20:
                    subset_cefr_samples.append((row["word"], cefr))

        total = sum(counts.values())
        print(f"definitions-empty anomalies: {total}")
        for tier in ("high", "medium", "low"):
            print(f"{tier}: {counts[tier]}")

        total_cefr = sum(all_cefr_counts.values())
        print(f"\ncefr_level total rows: {total_cefr}")
        print(f"cefr_level empty: {all_cefr_counts['empty']}")
        print(f"cefr_level valid: {all_cefr_counts['valid']}")
        print(f"cefr_level timestamp_like: {all_cefr_counts['timestamp_like']}")
        print(f"cefr_level other_invalid: {all_cefr_counts['other_invalid']}")
        if all_cefr_samples:
            print("[CEFR anomalies]")
            for word, cefr in all_cefr_samples:
                print(f"- {word}: {cefr}")

        subset_total = sum(subset_cefr_counts.values())
        print(f"\nsubset cefr_level rows (definitions empty + example/idioms/collocations): {subset_total}")
        print(f"subset cefr_level empty: {subset_cefr_counts['empty']}")
        print(f"subset cefr_level valid: {subset_cefr_counts['valid']}")
        print(f"subset cefr_level timestamp_like: {subset_cefr_counts['timestamp_like']}")
        print(f"subset cefr_level other_invalid: {subset_cefr_counts['other_invalid']}")
        if subset_cefr_samples:
            print("[Subset CEFR anomalies]")
            for word, cefr in subset_cefr_samples:
                print(f"- {word}: {cefr}")

        for tier in ("high", "medium", "low"):
            items = findings[tier]
            if not items:
                continue
            print(f"\n[{tier.upper()}]")
            for row in items[:limit]:
                source = (row["source"] or "").strip() or "(empty)"
                freq = row["frequency"] or 0
                cefr = row["cefr_level"] or ""
                flags = []
                if _nonempty_json_list(row["example"]):
                    flags.append("example")
                if _nonempty_json_list(row["idioms"]):
                    flags.append("idioms")
                if _nonempty_json_list(row["collocations"]):
                    flags.append("collocations")
                print(f"- {row['word']} [{source}] freq={freq} cefr={cefr} fields={','.join(flags)}")

        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit dictionary.db completeness")
    parser.add_argument("--db", default="data/dictionary.db", help="Path to dictionary.db")
    parser.add_argument("--limit", type=int, default=200, help="Max entries printed per severity")
    args = parser.parse_args()
    return audit(Path(args.db), args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
