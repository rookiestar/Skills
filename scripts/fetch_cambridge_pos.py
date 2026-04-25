#!/usr/bin/env python3
"""Fetch part-of-speech from Cambridge Dictionary for high-frequency words missing POS."""

from __future__ import annotations

import argparse
import concurrent.futures
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
URL_TEMPLATES = (
    "https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/{slug}",
    "https://dictionary.cambridge.org/us/dictionary/learner-english/{slug}",
    "https://dictionary.cambridge.org/us/dictionary/english/{slug}",
)
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9'’.-]*$")

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


def load_candidates(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT word, collins, oxford, bnc, frq, frequency
        FROM dictionary
        WHERE word IS NOT NULL
          AND TRIM(word) != ''
          AND COALESCE(TRIM(pos), '') = ''
          AND (collins > 0 OR oxford > 0 OR bnc > 0)
        ORDER BY
          CASE WHEN COALESCE(oxford, 0) > 0 THEN 0 ELSE 1 END,
          CASE WHEN COALESCE(collins, 0) > 0 THEN 0 ELSE 1 END,
          COALESCE(collins, 9999) ASC,
          COALESCE(bnc, 0) DESC,
          word ASC
        """
    ).fetchall()

    candidates: list[sqlite3.Row] = []
    for row in rows:
        word = row["word"].strip()
        if " " in word:
            continue
        if not WORD_RE.fullmatch(word):
            continue
        candidates.append(row)
        if len(candidates) >= limit:
            break
    return candidates


def extract_pos_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    # Primary: Cambridge uses <span class="pos"> or <span class="dpos">
    for selector in ("span.pos", "span.dpos", ".pos", "[data-type='pos']"):
        node = soup.select_one(selector)
        if node:
            text = node.get_text(strip=True).lower()
            if text in POS_KEYWORDS:
                return CAMBRIDGE_TO_ECDICT[text]
    # Fallback: scan header area for known POS keywords
    header = soup.select_one("div.entry-body, .def-block, .el")
    if header:
        header_text = header.get_text(" ", strip=True).lower()
        for keyword in POS_KEYWORDS:
            if keyword in header_text.split()[:20]:
                return CAMBRIDGE_TO_ECDICT[keyword]
    # Last resort: scan full text for POS pattern near the top
    text = soup.get_text(" ", strip=True).lower()
    for keyword in POS_KEYWORDS:
        idx = text.find(keyword)
        if idx != -1 and idx < 500:
            return CAMBRIDGE_TO_ECDICT[keyword]
    return None


def fetch_pos(word: str, timeout: int = 20) -> str | None:
    slug = quote(word.lower(), safe="")
    session = requests.Session()
    session.headers.update(HEADERS)
    for template in URL_TEMPLATES:
        url = template.format(slug=slug)
        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        pos = extract_pos_from_html(response.text)
        if pos:
            return pos
    return None


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row


def update_pos(
    db_path: Path,
    limit: int,
    workers: int,
    dry_run: bool,
    timeout: int,
    progress_every: int = 100,
) -> tuple[int, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        configure_connection(conn)
        candidates = load_candidates(conn, limit)
        if not candidates:
            return 0, 0

        updated = 0
        missing = 0
        processed = 0

        def worker(word: str) -> str | None:
            return fetch_pos(word, timeout=timeout)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(worker, row["word"]): row for row in candidates}
            for future in concurrent.futures.as_completed(future_map):
                row = future_map[future]
                processed += 1
                try:
                    result = future.result()
                except Exception:
                    missing += 1
                    continue

                if result is None:
                    missing += 1
                    continue

                updated += 1
                if not dry_run:
                    conn.execute(
                        """
                        UPDATE dictionary SET pos = ?, updated_at = datetime('now')
                        WHERE word = ?
                        """,
                        (result, row["word"]),
                    )
                if progress_every > 0 and processed % progress_every == 0:
                    mode = "dry-run" if dry_run else "updated"
                    print(
                        f"[cambridge-pos] {mode} processed={processed}/{len(candidates)} updated={updated} missing={missing}",
                        flush=True,
                    )
                    if not dry_run:
                        conn.commit()

        if not dry_run:
            conn.commit()
        return updated, missing
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Cambridge POS for high-frequency words missing POS")
    parser.add_argument("--db", required=True, help="Path to dictionary.db")
    parser.add_argument("--limit", type=int, default=4000, help="Max candidate words (default 4000)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent workers (default 8)")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout per request (default 20s)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't write to DB")
    parser.add_argument("--progress-every", type=int, default=100, help="Print progress every N words")
    args = parser.parse_args()

    updated, missing = update_pos(
        Path(args.db),
        limit=args.limit,
        workers=max(1, args.workers),
        dry_run=args.dry_run,
        timeout=args.timeout,
        progress_every=max(0, args.progress_every),
    )
    mode = "dry-run" if args.dry_run else "updated"
    print(f"[{mode}] total candidates: updated={updated}, missing={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
