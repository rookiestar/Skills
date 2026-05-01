#!/usr/bin/env python3
"""Preview router for the self-learning-tutor skill.

This script is only for local QA. It mirrors the intended routing boundary
described in SKILL.md so the project can be tested without a running OpenClaw
instance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lookup_router import classify_input


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview local routing for the skill")
    parser.add_argument("text", help="User input to classify")
    parser.add_argument("--last-term", default=None, help="Last queried term in session")
    args = parser.parse_args()

    result = classify_input(args.text, args.last_term)
    print(
        json.dumps(
            {
                "category": result.category,
                "reply_key": result.reply_key,
                **({"lookup_query": result.lookup_query} if result.lookup_query else {}),
                **({"reply_text": result.reply_text} if result.reply_text else {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
