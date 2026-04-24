#!/usr/bin/env python3
"""Fetch Cambridge examples for high-frequency words and store them locally."""

from __future__ import annotations

import argparse
import concurrent.futures
import re
import sqlite3
import sys
from dataclasses import dataclass
from html import unescape
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


@dataclass(frozen=True)
class CambridgeExample:
    word: str
    example: str
    example_source: str
    example_url: str


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row


def load_candidates(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT word, phonetic, pos, definition, translation, collins, oxford, tag,
               bnc, frq, frequency, example, example_source, example_url, source
        FROM dictionary
        WHERE word IS NOT NULL
          AND TRIM(word) != ''
          AND COALESCE(frq, 0) > 0
        ORDER BY
          CASE WHEN COALESCE(oxford, 0) > 0 THEN 0 ELSE 1 END,
          COALESCE(frq, 2147483647) ASC,
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


def clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?%])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text.strip()


def extract_example_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    containers = []
    first_block = soup.select_one("div.def-block")
    if first_block is not None:
        containers.append(first_block)
        containers.extend(first_block.select("div.daccord"))
    containers.append(soup)

    selectors = (
        "div.examp.dexamp",
        "li.eg.dexamp",
        "div.def-body div.examp.dexamp",
        "div.def-body li.eg.dexamp",
    )

    for container in containers:
        for selector in selectors:
            node = container.select_one(selector)
            if node is None:
                continue
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                return text
    return None


def fetch_example(word: str, timeout: int = 20) -> CambridgeExample | None:
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
        example = extract_example_from_html(response.text)
        if example:
            return CambridgeExample(word=word, example=example, example_source="cambridge", example_url=url)
    return None


def update_examples(
    db_path: Path,
    limit: int,
    workers: int,
    refresh: bool,
    timeout: int,
    progress_every: int = 0,
) -> tuple[int, int, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        configure_connection(conn)
        candidates = load_candidates(conn, limit)
        if not candidates:
            return 0, 0, 0

        to_fetch: list[sqlite3.Row] = []
        for row in candidates:
            if refresh:
                to_fetch.append(row)
                continue
            if not row["example"] or row["example_source"] != "cambridge":
                to_fetch.append(row)

        if not to_fetch:
            return 0, 0, len(candidates)

        updated = 0
        missing = 0
        processed = 0

        def worker(word: str) -> CambridgeExample | None:
            return fetch_example(word, timeout=timeout)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(worker, row["word"]): row for row in to_fetch}
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

                conn.execute(
                    """
                    UPDATE dictionary
                    SET example = ?, example_source = ?, example_url = ?, updated_at = datetime('now')
                    WHERE word = ?
                    """,
                    (result.example, result.example_source, result.example_url, result.word),
                )
                updated += 1
                if progress_every > 0 and processed % progress_every == 0:
                    print(
                        f"[cambridge] processed={processed}/{len(to_fetch)} updated={updated} missing={missing}",
                        flush=True,
                    )
                    conn.commit()

        conn.commit()
        return updated, missing, len(candidates)
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Cambridge examples for high-frequency words")
    parser.add_argument("--db", required=True, help="Path to dictionary.db")
    parser.add_argument("--limit", type=int, default=3500, help="Maximum number of candidate words")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent fetch workers")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout per request")
    parser.add_argument("--progress-every", type=int, default=100, help="Print progress every N processed words")
    parser.add_argument("--refresh", action="store_true", help="Refresh examples even if Cambridge already exists")
    args = parser.parse_args()

    updated, missing, total = update_examples(
        Path(args.db),
        limit=args.limit,
        workers=max(1, args.workers),
        refresh=args.refresh,
        timeout=args.timeout,
        progress_every=max(0, args.progress_every),
    )
    print(f"Checked {total} words, updated {updated}, missing {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
