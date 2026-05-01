#!/usr/bin/env python3
"""Regression tests for scripts/dict_lookup.py output formatting."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "dictionary.db"


def _lookup(mode: str, query: str) -> str:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "dict_lookup.py"),
            "--mode",
            mode,
            "--format",
            "text",
            "--db",
            str(DB_PATH),
            query,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return result.stdout


def _validate(text: str, mode: str) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "validate_lookup_output.py"),
            "--mode",
            mode,
        ],
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode, result.stderr.strip()


@pytest.mark.parametrize(
    ("query", "expect_phonetic", "expect_second_def"),
    [
        ("setup", True, True),
        ("important", True, True),
        ("in the future", True, True),
    ],
)
def test_en_to_zh_cards_match_validator(query: str, expect_phonetic: bool, expect_second_def: bool) -> None:
    output = _lookup("en_to_zh", query)
    rc, stderr = _validate(output, "en_to_zh")
    assert rc == 0, f"validator failed for {query}:\n{output}\nstderr: {stderr}"
    assert output.startswith(f"**{query}**")
    assert ("- 🔤 音标：" in output) is expect_phonetic
    assert ("- 🇨🇳 释义 2：" in output) is expect_second_def


@pytest.mark.parametrize(
    ("query", "expect_phonetic", "expect_second_english"),
    [
        ("期待", False, True),
        ("重要的", True, True),
        ("放弃", True, True),
    ],
)
def test_zh_to_en_cards_match_validator(query: str, expect_phonetic: bool, expect_second_english: bool) -> None:
    output = _lookup("zh_to_en", query)
    rc, stderr = _validate(output, "zh_to_en")
    assert rc == 0, f"validator failed for {query}:\n{output}\nstderr: {stderr}"
    assert output.startswith(f"**{query}**")
    assert ("- 🔤 音标：" in output) is expect_phonetic
    assert ("- 🔤 第二常用英文：" in output) is expect_second_english
