#!/usr/bin/env python3
"""Validate a lookup card against the strict skill output contract."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


FORBIDDEN_SNIPPETS = (
    "收到！",
    "词根",
    "生活化秒记",
    "发音提示",
    "常见搭配",
    "考试常考",
    "易混词辨析",
    "记忆锚点：",
    "絮音记忆锚点：",
    "AI领域",
    "领域用法",
    "更多意思",
    "还想了解",
    "总结",
    "追问",
)

NOT_FOUND_RE = re.compile(r"^📖 '.+' 这个词/短语暂时不在我的词典库中呢$")
NEW_SENSE_RE = re.compile(r"^(?:- )?\d+\.\s+.+$")
OLD_SENSE_RE = re.compile(r"^- 🇨🇳 释义(?: 2)?:")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def _normalize(text: str) -> list[str]:
    return [line.rstrip() for line in text.strip().splitlines() if line.strip()]


def _validate_old_en_to_zh(lines: list[str], start: int) -> list[str]:
    errors: list[str] = []
    cursor = start
    # Legacy format: optional phonetic handled by caller, then definition lines,
    # followed by one pooled example line.
    if cursor < len(lines) and OLD_SENSE_RE.fullmatch(lines[cursor]):
        cursor += 1
    else:
        errors.append(f"line {cursor + 1} must start with - 🇨🇳 释义：")
        return errors
    if cursor < len(lines) and OLD_SENSE_RE.fullmatch(lines[cursor]):
        cursor += 1
    if cursor < len(lines) and lines[cursor].startswith("- 💬 例句："):
        cursor += 1
    if len(lines) != cursor:
        errors.append(f"unexpected extra line: {lines[cursor] if cursor < len(lines) else lines[-1]}")
    return errors


def _validate_new_en_to_zh(lines: list[str], start: int) -> list[str]:
    errors: list[str] = []
    cursor = start
    sense_count = 0
    while cursor < len(lines):
        line = lines[cursor]
        if not NEW_SENSE_RE.fullmatch(line):
            errors.append(f"line {cursor + 1} must start with 1. / 2. / ... or - 1. / - 2. / ... : {line}")
            return errors
        sense_count += 1
        cursor += 1
        while cursor < len(lines):
            next_line = lines[cursor]
            if NEW_SENSE_RE.fullmatch(next_line):
                break
            if next_line.startswith("- "):
                errors.append(f"line {cursor + 1} must not start with a new bullet outside a sense block: {next_line}")
                return errors
            cursor += 1
    if sense_count == 0:
        errors.append("en_to_zh card is missing required sense blocks")
    return errors


def validate(text: str, mode: str) -> ValidationResult:
    lines = _normalize(text)
    errors: list[str] = []
    if not lines:
        return ValidationResult(False, ["response is empty"])

    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            errors.append(f"contains forbidden snippet: {snippet}")

    if len(lines) == 1 and NOT_FOUND_RE.fullmatch(lines[0]):
        return ValidationResult(not errors, errors)

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
            cursor += 1
        if cursor >= len(lines):
            errors.append("en_to_zh card is missing required sense blocks")
            return ValidationResult(False, errors)
        if NEW_SENSE_RE.fullmatch(lines[cursor]):
            errors.extend(_validate_new_en_to_zh(lines, cursor))
        else:
            errors.extend(_validate_old_en_to_zh(lines, cursor))
        return ValidationResult(not errors, errors)
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
