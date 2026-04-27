#!/usr/bin/env python3
"""Validate a lookup card against the strict skill output contract."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


FORBIDDEN_SNIPPETS = (
    "词根",
    "记忆",
    "发音提示",
    "常见搭配",
    "AI领域",
    "领域用法",
    "更多意思",
    "还想了解",
    "总结",
    "追问",
)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def _normalize(text: str) -> list[str]:
    return [line.rstrip() for line in text.strip().splitlines() if line.strip()]


def validate(text: str, mode: str) -> ValidationResult:
    lines = _normalize(text)
    errors: list[str] = []
    if not lines:
        return ValidationResult(False, ["response is empty"])

    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            errors.append(f"contains forbidden snippet: {snippet}")

    if mode == "en_to_zh":
        if not re.fullmatch(r"^\*\*.+\*\*$", lines[0]):
            errors.append(f"line 1 does not match the header template: {lines[0]}")
        if len(lines) < 3:
            errors.append("en_to_zh card is missing required lines")
            return ValidationResult(False, errors)
        expected_prefixes = ["- 🔤 音标：", "- 🇨🇳 释义："]
        for offset, prefix in enumerate(expected_prefixes, start=1):
            if not lines[offset].startswith(prefix):
                errors.append(f"line {offset + 1} must start with {prefix}")
        cursor = 3
        if len(lines) > cursor and lines[cursor].startswith("- 🇨🇳 释义 2："):
            cursor += 1
        if len(lines) > cursor and lines[cursor].startswith("- 💬 例句："):
            cursor += 1
        if len(lines) != cursor:
            errors.append(f"unexpected extra line: {lines[cursor] if cursor < len(lines) else lines[-1]}")
    else:
        if not re.fullmatch(r"^\*\*.+\*\*$", lines[0]):
            errors.append(f"line 1 does not match the header template: {lines[0]}")
        if len(lines) < 4:
            errors.append("zh_to_en card is missing required lines")
            return ValidationResult(False, errors)
        expected_prefixes = ["- 🔤 最常用英文：", "- 🔤 音标：", "- 🇨🇳 对应义："]
        cursor = 1
        if not lines[cursor].startswith(expected_prefixes[0]):
            errors.append(f"line 2 must start with {expected_prefixes[0]}")
        cursor += 1
        if cursor < len(lines) and lines[cursor].startswith("- 🔤 第二常用英文："):
            cursor += 1
        for prefix in expected_prefixes[1:]:
            if cursor >= len(lines) or not lines[cursor].startswith(prefix):
                errors.append(f"line {cursor + 1} must start with {prefix}")
                return ValidationResult(False, errors)
            cursor += 1
        if cursor < len(lines) and lines[cursor].startswith("- 💬 例句："):
            cursor += 1
        if len(lines) != cursor:
            errors.append(f"unexpected extra line: {lines[cursor] if cursor < len(lines) else lines[-1]}")

    return ValidationResult(not errors, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a lookup card")
    parser.add_argument(
        "--mode",
        required=True,
        choices=("en_to_zh", "zh_to_en"),
        help="Card type to validate",
    )
    args = parser.parse_args()

    raw = sys.stdin.read()
    result = validate(raw, args.mode)
    if result.ok:
        print("OK")
        return 0

    for error in result.errors:
        print(error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
