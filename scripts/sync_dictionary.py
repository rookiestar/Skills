#!/usr/bin/env python3
"""Download ECDICT, import it, and refresh Cambridge examples."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_cambridge_examples import update_examples  # noqa: E402
from scripts.import_ecdict import import_source  # noqa: E402


DEFAULT_ECDICT_URL = "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"


def download_file(url: str, dest_path: Path, timeout: int = 60) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    with requests.get(url, headers=headers, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with dest_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download ECDICT, import it, and refresh Cambridge examples")
    parser.add_argument("--source", default=None, help="Optional local source file path")
    parser.add_argument("--source-url", default=DEFAULT_ECDICT_URL, help="ECDICT CSV download URL")
    parser.add_argument("--db", default=str(ROOT / "data" / "dictionary.db"), help="Path to dictionary.db")
    parser.add_argument("--limit", type=int, default=3500, help="High-frequency word limit for Cambridge sync")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent Cambridge fetch workers")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout per Cambridge request")
    parser.add_argument("--refresh", action="store_true", help="Refresh Cambridge examples even if present")
    args = parser.parse_args()

    db_path = Path(args.db)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        if args.source:
            source_path = Path(args.source)
        else:
            source_path = tmp_path / "ecdict.csv"
            print(f"Downloading ECDICT from {args.source_url}")
            download_file(args.source_url, source_path)

        print(f"Importing ECDICT into {db_path}")
        imported, reverse_rows = import_source(source_path, db_path)
        print(f"Imported {imported} entries and {reverse_rows} reverse rows")

    print(f"Refreshing Cambridge examples for top {args.limit} high-frequency words")
    updated, missing, total = update_examples(
        db_path,
        limit=args.limit,
        workers=max(1, args.workers),
        refresh=args.refresh,
        timeout=args.timeout,
        progress_every=100,
    )
    print(f"Checked {total} words, updated {updated}, missing {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
