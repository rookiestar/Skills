#!/usr/bin/env python3
"""Build dictionary.db entirely from Cambridge Dictionary.

Reads a wordlist file, fetches each word's page from Cambridge Dictionary,
extracts all fields (phonetics, definitions with embedded POS, translations, examples, CEFR),
and writes structured records into dictionary.sqlite.

Usage:
    python3 scripts/build_cambridge_dict.py --wordlist data/cambridge_wordlist.txt --db data/dictionary.db
    python3 scripts/build_cambridge_dict.py --wordlist data/prototype_wordlist.txt --db data/dictionary.db --dry-run
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import time
import threading
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

USER_AGENTS = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
)
URL_TEMPLATES = (
    "https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/{slug}",
    "https://dictionary.cambridge.org/us/dictionary/learner-english/{slug}",
    "https://dictionary.cambridge.org/us/dictionary/english/{slug}",
)
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9'’.-]*$")
CEFR_RE = re.compile(r"[A-C][12]")

CAMBRIDGE_TO_ECDICT: dict[str, str] = {
    "noun": "n.",
    "verb": "v.",
    "adjective": "a.",
    "adverb": "adv.",
    "preposition": "prep.",
    "pronoun": "pron.",
    "conjunction": "conj.",
    "interjection": "int.",
    "exclamation": "int.",
    "determiner": "det.",
}
POS_KEYWORDS = frozenset(CAMBRIDGE_TO_ECDICT.keys())


@dataclass
class CambridgeEntry:
    word: str
    phonetic_uk: str = ""
    phonetic_us: str = ""
    definition: str = ""
    translation: str = ""
    definitions: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    cefr_level: str = ""
    source_url: str = ""


def clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?%])", r"\1", text)
    return text.strip()


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


def extract_cefr(block) -> str | None:
    for sel in ("[class*='epp-xref']", "[class*='epp']", ".cc"):
        node = block.select_one(sel)
        if node:
            m = CEFR_RE.search(node.get_text())
            if m:
                return m.group(0)
    return None


def extract_entry(html: str, word: str, url: str) -> CambridgeEntry | None:
    soup = BeautifulSoup(html, "html.parser")
    entry = soup.select_one(".entry-body")
    if not entry:
        return None

    # Word
    hw_node = entry.select_one(".hw")
    if not hw_node:
        return None

    result = CambridgeEntry(word=word, source_url=url)

    # Entry-level POS (for def-blocks that lack per-block POS)
    entry_pos_node = entry.select_one(".pos, .dpos")
    default_pos = ""
    if entry_pos_node:
        ep = entry_pos_node.get_text(strip=True).lower()
        if ep in CAMBRIDGE_TO_ECDICT:
            default_pos = CAMBRIDGE_TO_ECDICT[ep] + " "

    # Phonetics UK
    uk_block = entry.select_one(".uk")
    if uk_block:
        ipa = uk_block.select_one(".pron, .ipa")
        if ipa:
            result.phonetic_uk = clean_text(ipa.get_text())

    # Phonetics US
    us_block = entry.select_one(".us")
    if us_block:
        ipa = us_block.select_one(".pron, .ipa")
        if ipa:
            result.phonetic_us = clean_text(ipa.get_text())

    # Senses: collect from both def-block (verb) and dsense (noun/other) blocks
    def_blocks = soup.select("div.def-block")
    dsense_blocks = soup.select(".dsense")
    all_blocks = list(def_blocks) + list(dsense_blocks)

    if not all_blocks:
        # Fallback: try single def in entry body
        def_node = entry.select_one(".def")
        trans_node = entry.select_one(".trans")
        ex_node = entry.select_one(".examp.dexamp, li.eg.dexamp")
        if def_node:
            result.definition = clean_text(def_node.get_text())
        if trans_node:
            result.translation = clean_text(trans_node.get_text())
        if ex_node:
            result.examples.append(clean_text(ex_node.get_text(" ", strip=True)))
        fallback_def = result.translation or result.definition
        if fallback_def and fallback_def not in result.definitions:
            result.definitions.append(fallback_def)
        if not result.cefr_level:
            cefr = extract_cefr(entry)
            if cefr:
                result.cefr_level = cefr
        return result

    # Per-POS caps to ensure diversity (verb-heavy pages won't crowd out noun/adj)
    pos_caps = {"v.": 8, "n.": 5, "a.": 3, "adv.": 2}
    pos_counts: dict[str, int] = {}

    for block in all_blocks:
        def_node = block.select_one(".def")
        trans_node = block.select_one(".trans")
        ex_node = block.select_one(".examp.dexamp, li.eg.dexamp")

        def_text = clean_text(def_node.get_text()) if def_node else ""
        trans_text = clean_text(trans_node.get_text()) if trans_node else ""

        # Per-block POS: try dsense_h > pos first, then block-level pos/dpos
        block_pos_node = (
            block.select_one(".dsense_h .pos, .dsense_h .dpos")
            or block.select_one(".pos, .dpos")
        )
        pos_prefix = ""
        current_pos = ""
        if block_pos_node:
            p = block_pos_node.get_text(strip=True).lower()
            if p in CAMBRIDGE_TO_ECDICT:
                current_pos = CAMBRIDGE_TO_ECDICT[p]
                pos_prefix = current_pos + " "
        elif default_pos:
            pos_prefix = default_pos
            current_pos = default_pos.strip()

        # Skip if this POS already has enough entries
        if current_pos and pos_counts.get(current_pos, 0) >= pos_caps.get(current_pos, 99):
            continue

        if first := not result.definition:
            result.definition = def_text
            result.translation = trans_text
            cefr = extract_cefr(block)
            if cefr:
                result.cefr_level = cefr

        full_def = f"{pos_prefix}{trans_text or def_text}"
        if full_def and full_def not in result.definitions:
            result.definitions.append(full_def)
            # Only count toward POS cap when we actually detected a POS prefix
            if current_pos:
                pos_counts[current_pos] = pos_counts.get(current_pos, 0) + 1

        if ex_node:
            ex_text = clean_text(ex_node.get_text(" ", strip=True))
            result.examples.append(ex_text)

        if len(result.definitions) >= 15:
            break

    if not result.definitions:
        fallback_def = result.translation or result.definition
        if fallback_def:
            result.definitions.append(fallback_def)

    return result


def load_wordlist(path: Path) -> list[str]:
    words: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        w = line.split(",")[0].strip()
        if not w or w.startswith("#"):
            continue
        if WORD_RE.fullmatch(w):
            words.append(w)
    return words


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS dictionary (
            word TEXT PRIMARY KEY,
            phonetic TEXT,
            phonetic_uk TEXT,
            phonetic_us TEXT,
            translation TEXT,
            definitions TEXT,
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
        """
    )
    try:
        conn.execute("ALTER TABLE dictionary ADD COLUMN cefr_level TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # column already exists


def already_fetched(conn: sqlite3.Connection, word: str) -> bool:
    row = conn.execute(
        "SELECT definitions FROM dictionary WHERE word = ? AND source = 'cambridge'",
        (word,),
    ).fetchone()
    return bool(row and _nonempty_json_list(row["definitions"]))


def build_reverse_terms(definitions: list[str]) -> list[str]:
    from scripts.dictionary_utils import normalize_zh_term, SPLIT_RE

    results: list[str] = []
    seen: set[str] = set()
    for item in definitions:
        for piece in SPLIT_RE.split(item):
            candidate = normalize_zh_term(piece)
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            results.append(candidate)
    return results


def write_entry(conn: sqlite3.Connection, entry: CambridgeEntry) -> None:
    definitions_json = json.dumps(entry.definitions, ensure_ascii=False) if entry.definitions else "[]"
    examples_json = json.dumps(entry.examples, ensure_ascii=False) if entry.examples else "[]"
    existing = conn.execute(
        "SELECT 1 FROM dictionary WHERE word = ? LIMIT 1",
        (entry.word,),
    ).fetchone()

    conn.execute(
        "DELETE FROM dictionary_reverse WHERE word = ? AND source = 'cambridge'",
        (entry.word,),
    )
    if existing:
        conn.execute(
            """
            UPDATE dictionary
               SET phonetic = ?,
                   phonetic_uk = ?,
                   phonetic_us = ?,
                   translation = ?,
                   definitions = ?,
                   example = ?,
                   example_source = ?,
                   example_url = ?,
                   source = ?,
                   updated_at = datetime('now'),
                   cefr_level = ?
             WHERE word = ?
            """,
            (
                entry.phonetic_us or entry.phonetic_uk,
                entry.phonetic_uk,
                entry.phonetic_us,
                entry.translation,
                definitions_json,
                examples_json,
                "cambridge",
                entry.source_url,
                "cambridge",
                entry.cefr_level,
                entry.word,
            ),
        )
    else:
        conn.execute(
            """
        INSERT INTO dictionary
            (word, phonetic, phonetic_uk, phonetic_us, translation,
             definitions, example, example_source, example_url, source, updated_at, cefr_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """,
            (
                entry.word,
                entry.phonetic_us or entry.phonetic_uk,
                entry.phonetic_uk,
                entry.phonetic_us,
                entry.translation,
                definitions_json,
                examples_json,
                "cambridge",
                entry.source_url,
                "cambridge",
                entry.cefr_level,
            ),
        )

    # Reverse index
    reverse_terms = build_reverse_terms(entry.definitions)
    if entry.translation and entry.translation not in reverse_terms:
        reverse_terms.insert(0, entry.translation)

    for rank, term in enumerate(reverse_terms[:5]):
        conn.execute(
            """INSERT INTO dictionary_reverse
               (zh_term, word, phonetic, source, sense_rank)
               VALUES (?, ?, ?, ?, ?)""",
            (term, entry.word, entry.phonetic_us or entry.phonetic_uk, "cambridge", rank),
        )


class RequestThrottle:
    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = max(0.0, min_interval_s)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self.min_interval_s <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait_for = self._next_allowed - now
            if wait_for > 0:
                time.sleep(wait_for)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval_s + random.uniform(0, self.min_interval_s * 0.25)


def fetch_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = 2,
    timeout: int = 20,
    throttle: RequestThrottle | None = None,
) -> str | None:
    for attempt in range(max_retries + 1):
        session.headers["User-Agent"] = random.choice(USER_AGENTS)
        try:
            if throttle is not None:
                throttle.wait()
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  [rate-limited] waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code in (403, 503):
                wait = 10 * (attempt + 1)
                print(f"  [blocked {resp.status_code}] waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            return None
    return None


def run_build(
    db_path: Path,
    wordlist_path: Path,
    workers: int = 1,
    dry_run: bool = False,
    timeout: int = 20,
    delay: float = 1.5,
    skip_existing: bool = True,
    progress_every: int = 50,
) -> dict[str, int]:
    words = load_wordlist(wordlist_path)
    if not words:
        print("Wordlist is empty!", file=sys.stderr)
        return {"total": 0, "updated": 0, "missing": 0, "skipped": 0}

    print(f"Loaded {len(words)} words from {wordlist_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        configure_connection(conn)
        ensure_schema(conn)

        if skip_existing:
            before = len(words)
            words = [w for w in words if not already_fetched(conn, w)]
            skipped = before - len(words)
            print(f"Skipping {skipped} already-fetched words, {len(words)} remaining")
        else:
            skipped = 0

        if not words:
            return {"total": len(load_wordlist(wordlist_path)), "updated": 0, "missing": 0, "skipped": skipped}

        throttle = RequestThrottle(delay)

        updated = 0
        missing = 0
        processed = 0
        total = len(words)

        def worker(word: str) -> CambridgeEntry | None:
            session = requests.Session()
            session.headers.update({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            slug = quote(word.lower(), safe="")
            for template in URL_TEMPLATES:
                url = template.format(slug=slug)
                html = fetch_with_retry(session, url, timeout=timeout, throttle=throttle)
                if html:
                    entry = extract_entry(html, word, url)
                    if entry and entry.definitions:
                        return entry
            return None

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(worker, w): w for w in words}
            for future in concurrent.futures.as_completed(future_map):
                word = future_map[future]
                processed += 1
                try:
                    entry = future.result()
                except Exception:
                    missing += 1
                    continue

                if entry is None:
                    missing += 1
                    continue

                updated += 1
                if not dry_run:
                    write_entry(conn, entry)

                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total - processed) / rate if rate > 0 else 0

                if progress_every > 0 and processed % progress_every == 0:
                    mode = "dry-run" if dry_run else "built"
                    print(
                        f"[{mode}] {processed}/{total} "
                        f"updated={updated} missing={missing} "
                        f"({rate:.1f} word/s ETA:{eta:.0f}s)",
                        flush=True,
                    )
                    if not dry_run:
                        conn.commit()

        if not dry_run:
            conn.commit()

        elapsed = time.time() - start_time
        return {
            "total": total,
            "updated": updated,
            "missing": missing,
            "skipped": skipped,
            "elapsed_s": round(elapsed, 1),
        }
    finally:
        conn.close()


# Lazy import to avoid top-level dependency on concurrent.futures when not needed
import concurrent.futures


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dictionary.db from Cambridge Dictionary")
    parser.add_argument("--wordlist", required=True, help="Path to wordlist file (one word per line)")
    parser.add_argument("--db", required=True, help="Path to output dictionary.db")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent workers (default 1)")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout per request (default 20s)")
    parser.add_argument("--delay", type=float, default=1.5, help="Minimum seconds between HTTP requests (default 1.5)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't write to DB")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip already-fetched words")
    parser.add_argument("--progress-every", type=int, default=50, help="Print progress every N words")
    args = parser.parse_args()

    stats = run_build(
        db_path=Path(args.db),
        wordlist_path=Path(args.wordlist),
        workers=max(1, args.workers),
        dry_run=args.dry_run,
        timeout=args.timeout,
        delay=max(0.0, args.delay),
        skip_existing=not args.no_skip,
        progress_every=max(0, args.progress_every),
    )

    mode = "dry-run" if args.dry_run else "built"
    print(
        f"\n[{mode}] done: total={stats['total']} updated={stats['updated']} "
        f"missing={stats['missing']} skipped={stats['skipped']} "
        f"time={stats.get('elapsed_s', '?')}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
