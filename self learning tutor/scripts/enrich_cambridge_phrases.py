#!/usr/bin/env python3
"""Batch-enrich gaokao_phrases.json with definitions from Cambridge Dictionary.

Targets phrases that have empty definitions[] after the initial build.
Fetches each phrase's page from Cambridge Dictionary, extracts Chinese
translations + examples, and merges back into the JSON file.

Usage:
    python3 scripts/enrich_cambridge_phrases.py --input data/gaokao_phrases.json --output data/gaokao_phrases.json
    python3 scripts/enrich_cambridge_phrases.py --input data/gaokao_phrases.json --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

USER_AGENTS = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
)

URL_TEMPLATE = (
    "https://dictionary.cambridge.org/dictionary/english-chinese-simplified/{slug}"
)
CEFR_RE = re.compile(r"[A-C][12]")

CAMBRIDGE_TO_ECDICT: dict[str, str] = {
    "noun": "n.", "verb": "v.", "adjective": "a.", "adverb": "adv.",
    "preposition": "prep.", "pronoun": "pron.", "conjunction": "conj.",
}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Phrase → URL slug
# ---------------------------------------------------------------------------


def phrase_to_slug(phrase: str) -> str:
    """Convert a phrase like 'look forward to' → 'look-forward-to'."""
    return phrase.strip().lower().replace(" ", "-")


# ---------------------------------------------------------------------------
# Find phrases needing enrichment
# ---------------------------------------------------------------------------


def find_no_def_phrases(json_path: str | Path) -> list[dict]:
    """Return entries from gaokao_phrases.json that have empty definitions[]."""
    data = json.loads(Path(json_path).read_text("utf-8"))
    return [p for p in data.get("phrases", []) if not p.get("definitions")]


# ---------------------------------------------------------------------------
# HTML extraction (adapted from build_cambridge_dict.py for phrases)
# ---------------------------------------------------------------------------


def clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?%])", r"\1", text)
    return text.strip()


def extract_entry(html: str, word: str, url: str) -> CambridgeEntry | None:
    soup = BeautifulSoup(html, "html.parser")
    entry = soup.select_one(".entry-body")
    if not entry:
        return None

    hw_node = entry.select_one(".hw")
    if not hw_node:
        return None

    result = CambridgeEntry(word=word, source_url=url)

    # Phonetics
    uk_block = entry.select_one(".uk")
    if uk_block:
        ipa = uk_block.select_one(".pron, .ipa")
        if ipa:
            result.phonetic_uk = clean_text(ipa.get_text())
    us_block = entry.select_one(".us")
    if us_block:
        ipa = us_block.select_one(".pron, .ipa")
        if ipa:
            result.phonetic_us = clean_text(ipa.get_text())

    # Senses
    def_blocks = soup.select("div.def-block")
    dsense_blocks = soup.select(".dsense")
    all_blocks = list(def_blocks) + list(dsense_blocks)

    if not all_blocks:
        def_node = entry.select_one(".def")
        trans_node = entry.select_one(".trans")
        ex_node = entry.select_one("li.eg.dexamp, .examp.dexamp")
        if def_node:
            result.definition = clean_text(def_node.get_text())
        if trans_node:
            result.translation = clean_text(trans_node.get_text())
        if ex_node:
            result.examples.append(clean_text(ex_node.get_text(" ", strip=True)))
        return result

    for block in all_blocks[:10]:
        def_node = block.select_one(".def")
        trans_node = block.select_one(".trans")
        ex_node = block.select_one("li.eg.dexamp, .examp.dexamp")

        def_text = clean_text(def_node.get_text()) if def_node else ""
        trans_text = clean_text(trans_node.get_text()) if trans_node else ""

        # POS prefix
        block_pos_node = (
            block.select_one(".dsense_h .pos, .dsense_h .dpos")
            or block.select_one(".pos, .dpos")
        )
        pos_prefix = ""
        if block_pos_node:
            p = block_pos_node.get_text(strip=True).lower()
            if p in CAMBRIDGE_TO_ECDICT:
                pos_prefix = CAMBRIDGE_TO_ECDICT[p] + " "

        if first := not result.definition:
            result.definition = def_text
            result.translation = trans_text

        full_def = f"{pos_prefix}{trans_text or def_text}".strip()
        if full_def and full_def not in result.definitions:
            result.definitions.append(full_def)

        if ex_node:
            ex_text = clean_text(ex_node.get_text(" ", strip=True))
            if ex_text and ex_text not in result.examples:
                result.examples.append(ex_text)

        if len(result.definitions) >= 5:
            break

    return result


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------


def fetch_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = 3,
    timeout: int = 20,
) -> str | None:
    for attempt in range(max_retries + 1):
        session.headers["User-Agent"] = random.choice(USER_AGENTS)
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  [429] waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code in (403, 503):
                wait = 15 * (attempt + 1) + random.uniform(0, 5)
                print(f"  [{resp.status_code}] waiting {wait:.0f}s...", flush=True)
                time.sleep(wait)
                continue
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(3 ** attempt)
                continue
            return None
    return None


# ---------------------------------------------------------------------------
# Enrichment merge
# ---------------------------------------------------------------------------


def enrich_phrase(original: dict, cam: CambridgeEntry) -> dict:
    """Merge Cambridge data into an existing phrase entry (mutates a copy)."""
    enriched = dict(original)

    # Add definitions (dedup against existing)
    new_defs = []
    for d in cam.definitions:
        d_clean = d.strip()
        if d_clean and d_clean not in original.get("definitions", []):
            new_defs.append(d_clean)
    if cam.translation and cam.translation not in original.get("definitions", []):
        t = cam.translation.strip()
        if t and t not in new_defs:
            new_defs.insert(0, t)
    enriched["definitions"] = original.get("definitions", []) + new_defs

    # Add example if missing
    if not original.get("examples") and cam.examples:
        raw_ex = cam.examples[0]
        if isinstance(raw_ex, dict):
            enriched["examples"] = [raw_ex]
        else:
            enriched["examples"] = [{"en": raw_ex, "zh": ""}]

    # Re-extract zh_terms now that we have definitions
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import build_phrase_db as bdb
        enriched["zh_terms"] = bdb.extract_zh_terms(enriched["definitions"])
    except ImportError:
        pass

    return enriched


# ---------------------------------------------------------------------------
# Card formatting (reused from build_phrase_db.py)
# ---------------------------------------------------------------------------


def format_card_en_to_zh(entry: dict) -> str:
    lines: list[str] = [f"**{entry['phrase']}**"]
    for i, d in enumerate(entry.get("definitions", [])[:2], 1):
        label = f"- 🇨🇳 释义：" if i == 1 else f"- 🇨🇳 释义 {i}："
        lines.append(f"{label}{d}")
    examples = entry.get("examples", [])
    if examples:
        ex = examples[0]
        lines.append(f"- 💬 例句：{ex['en']}（{ex['zh']}）")
    return "\n".join(lines)


def format_card_zh_to_en(entry: dict, query: str) -> str:
    lines: list[str] = [f"**{query}**"]
    phonetic = entry.get("phonetic")
    lines.append(f"- 🔤 最常用英文：{entry['phrase']}" + (f" {phonetic}" if phonetic else ""))
    if phonetic:
        lines.append(f"- 🔤 音标：{phonetic}")
    # Phrase format: 1 def max; Word format (with phonetic): 2 defs max
    max_defs = 2 if phonetic else 1
    for i, d in enumerate(entry.get("definitions", [])[:max_defs], 1):
        label = f"- 🇨🇳 对应义：" if i == 1 else f"- 🇨🇳 对应义 {i}："
        lines.append(f"{label}{d}")
    examples = entry.get("examples", [])
    if examples:
        ex = examples[0]
        lines.append(f"- 💬 例句：{ex['en']}（{ex['zh']}）")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_enrich(
    input_path: Path,
    output_path: Path | None = None,
    workers: int = 1,
    dry_run: bool = False,
    timeout: int = 20,
    progress_every: int = 20,
    delay: float = 2.0,
) -> dict[str, int]:
    output_path = output_path or input_path

    data = json.loads(input_path.read_text("utf-8"))
    phrases = data.get("phrases", [])
    total_phrases = len(phrases)

    # Identify targets
    no_defs = [p for p in phrases if not p.get("definitions")]
    print(f"[Input] {total_phrases} total phrases, {len(no_defs)} without definitions ({len(no_defs)*100//max(total_phrases,1)}%)")

    if not no_defs:
        print("[Enrich] All phrases already have definitions — nothing to do.")
        return {"total": total_phrases, "targeted": 0, "enriched": 0, "missing": 0}

    # Fetch from Cambridge
    session = requests.Session()
    session.headers.update({
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })

    enriched_count = 0
    missing_count = 0
    processed = 0
    target_count = len(no_defs)

    start_time = time.time()

    def worker(entry: dict) -> tuple[dict, CambridgeEntry | None] | None:
        phrase = entry["phrase"]
        slug = phrase_to_slug(phrase)
        url = URL_TEMPLATE.format(slug=slug)
        html = fetch_with_retry(session, url, timeout=timeout)
        if not html:
            return None
        cam = extract_entry(html, phrase, url)
        if cam is None:
            return None
        return (entry, cam)

    import concurrent.futures

    # Sequential mode with delay: avoids rate limiting
    if workers <= 1:
        for entry in no_defs:
            processed += 1
            try:
                result = worker(entry)
            except Exception:
                missing_count += 1
                if delay > 0:
                    time.sleep(delay)
                continue

            if result is None:
                missing_count += 1
                if delay > 0:
                    time.sleep(delay)
                continue

            original_entry, cam_entry = result
            for i, p in enumerate(phrases):
                if p["phrase"] == original_entry["phrase"]:
                    phrases[i] = enrich_phrase(p, cam_entry)
                    break
            enriched_count += 1

            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (target_count - processed) / rate if rate > 0 else 0

            if progress_every > 0 and processed % progress_every == 0:
                mode = "dry-run" if dry_run else "enriched"
                print(
                    f"[{mode}] {processed}/{target_count} "
                    f"enriched={enriched_count} missing={missing_count} "
                    f"({rate:.1f}/s ETA:{eta:.0f}s)",
                    flush=True,
                )

            if delay > 0 and processed < target_count:
                time.sleep(delay + random.uniform(0, 1))
    else:
        # Parallel mode (original)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(worker, e): e for e in no_defs}
            for future in concurrent.futures.as_completed(future_map):
                processed += 1
                try:
                    result = future.result()
                except Exception:
                    missing_count += 1
                    continue

                if result is None:
                    missing_count += 1
                    continue

                original_entry, cam_entry = result
                for i, p in enumerate(phrases):
                    if p["phrase"] == original_entry["phrase"]:
                        phrases[i] = enrich_phrase(p, cam_entry)
                        break
                enriched_count += 1

                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (target_count - processed) / rate if rate > 0 else 0

                if progress_every > 0 and processed % progress_every == 0:
                    mode = "dry-run" if dry_run else "enriched"
                    print(
                        f"[{mode}] {processed}/{target_count} "
                        f"enriched={enriched_count} missing={missing_count} "
                        f"({rate:.1f}/s ETA:{eta:.0f}s)",
                        flush=True,
                    )

    # Recompute stats
    with_def = sum(1 for p in phrases if p.get("definitions"))
    with_ex = sum(1 for p in phrases if p.get("examples"))

    data["stats"]["with_definitions"] = with_def
    data["stats"]["with_examples"] = with_ex
    data["phrases"] = phrases

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        size = output_path.stat().st_size
        print(f"\n[Wrote] {output_path} ({size:,} bytes)")
    else:
        print("\n[DRY RUN] No files written.")

    elapsed = time.time() - start_time
    return {
        "total": total_phrases,
        "targeted": target_count,
        "enriched": enriched_count,
        "missing": missing_count,
        "final_with_def": with_def,
        "elapsed_s": round(elapsed, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich phrases from Cambridge Dictionary")
    parser.add_argument("--input", required=True, help="Path to gaokao_phrases.json")
    parser.add_argument("--output", default=None, help="Output path (default: same as input)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers (default 4)")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout per request (default 20s)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    parser.add_argument("--progress-every", type=int, default=20, help="Print progress every N phrases")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests (default 2.0, for sequential mode)")
    args = parser.parse_args()

    stats = run_enrich(
        input_path=Path(args.input),
        output_path=Path(args.output) if args.output else None,
        workers=max(1, args.workers),
        dry_run=args.dry_run,
        timeout=args.timeout,
        progress_every=max(0, args.progress_every),
        delay=max(0, args.delay),
    )

    mode = "DRY RUN" if args.dry_run else "ENRICHED"
    print(
        f"\n[{mode}] done: total={stats['total']} targeted={stats['targeted']} "
        f"enriched={stats['enriched']} missing={stats['missing']} "
        f"final_with_def={stats['final_with_def']} time={stats.get('elapsed_s', '?')}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
