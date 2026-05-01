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
        if len(lines) < 2:
            errors.append("en_to_zh card is missing required lines")
            return ValidationResult(False, errors)
        cursor = 1
        if cursor < len(lines) and lines[cursor].startswith("- 📖 词性："):
            cursor += 1
        # Phrase format (no phonetic line): **word** → 🇨🇳释义 → 💬 例句
        # Word format (with phonetic): **word** → 🔤 音标 → 🇨🇳释义 → 💬 例句
        has_phonetic = cursor < len(lines) and lines[cursor].startswith("- 🔤 音标：")
        if has_phonetic:
            expected_prefixes = ["- 🔤 音标：", "- 🇨🇳 释义："]
        else:
            expected_prefixes = ["- 🇨🇳 释义："]
        for prefix in expected_prefixes:
            if cursor >= len(lines) or not lines[cursor].startswith(prefix):
                errors.append(f"line {cursor + 1} must start with {prefix}")
                break
            cursor += 1
        if cursor < len(lines) and lines[cursor].startswith("- 🇨🇳 释义 2："):
            cursor += 1
        if cursor < len(lines) and lines[cursor].startswith("- 💬 例句："):
            cursor += 1
        if len(lines) != cursor:
            errors.append(f"unexpected extra line: {lines[cursor] if cursor < len(lines) else lines[-1]}")
    else:
        if not re.fullmatch(r"^\*\*.+\*\*$", lines[0]):
            errors.append(f"line 1 does not match the header template: {lines[0]}")
        if len(lines) < 4:
            errors.append("zh_to_en card is missing required lines")
            return ValidationResult(False, errors)
        cursor = 1
        if not lines[cursor].startswith("- 🔤 最常用英文："):
            errors.append(f"line 2 must start with - 🔤 最常用英文：")
        cursor += 1
        # Consume optional second English line before the phonetic line.
        if cursor < len(lines) and lines[cursor].startswith("- 🔤 第二常用英文："):
            cursor += 1
        # Detect format: line 2 contains /phonetic/ → phonetic line is required.
        has_phonetic = "/" in lines[1]
        if cursor < len(lines) and lines[cursor].startswith("- 🔤 音标："):
            cursor += 1
        elif has_phonetic:
            errors.append(f"line {cursor + 1} must start with - 🔤 音标：")
            return ValidationResult(False, errors)
        if cursor >= len(lines) or not lines[cursor].startswith("- 🇨🇳 对应义："):
            errors.append(f"line {cursor + 1} must start with - 🇨🇳 对应义：")
        else:
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
