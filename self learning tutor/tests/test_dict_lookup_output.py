#!/usr/bin/env python3
"""Regression tests for scripts/dict_lookup.py output formatting."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import re
import json

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


def _lookup_result(mode: str, query: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "dict_lookup.py"),
            "--mode",
            mode,
            "--format",
            "text",
            "--style",
            "strict",
            "--db",
            str(DB_PATH),
            query,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )


def _lookup_json(mode: str, query: str) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "dict_lookup.py"),
            "--mode",
            mode,
            "--format",
            "json",
            "--db",
            str(DB_PATH),
            query,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return json.loads(result.stdout)


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
    ("query", "expect_phonetic"),
    [
        ("setup", True),
        ("important", True),
        ("in the future", True),
    ],
)
def test_en_to_zh_cards_match_validator(query: str, expect_phonetic: bool) -> None:
    output = _lookup("en_to_zh", query)
    rc, stderr = _validate(output, "en_to_zh")
    assert rc == 0, f"validator failed for {query}:\n{output}\nstderr: {stderr}"
    assert output.startswith(f"**{query}**")
    assert ("🔤 音标：" in output) is expect_phonetic
    assert re.search(r"(?m)^\*\*1\.\*\*\s+", output)
    assert not re.search(r"(?m)^- \*\*\d+\.\*\*\s+", output)
    assert re.search(r"(?ms)^\*\*1\.\*\*\s+.+\n\n>\s+💬 ", output)
    assert "- 🇨🇳 释义：" not in output
    assert "- 💬 例句：" not in output


def test_en_to_zh_examples_stay_bound_to_each_sense() -> None:
    output = _lookup("en_to_zh", "trace")
    rc, stderr = _validate(output, "en_to_zh")
    assert rc == 0, f"validator failed for trace:\n{output}\nstderr: {stderr}"
    assert re.search(r"(?ms)^\*\*1\.\*\*\s+.+\n\n>\s+💬 ", output)
    assert re.search(r"(?m)^\*\*2\.\*\*\s+", output)


def test_json_lookup_includes_learning_material_fields() -> None:
    output = _lookup_json("en_to_zh", "quiet")
    assert output["word"] == "quiet"
    assert output["senses"]
    assert "collocations" in output
    assert "idioms" in output
    assert output["collocations"]
    assert all(item.get("phrase") for item in output["collocations"])


def test_json_lookup_filters_empty_idiom_fragments() -> None:
    output = _lookup_json("en_to_zh", "setup")
    assert output["word"] == "setup"
    assert output["senses"]
    assert output["idioms"] == []


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


@pytest.mark.parametrize(
    "forbidden",
    [
        "收到！看起来你想了解 setup 这个词",
        "生活化秒记：",
        "常见搭配（考试常考）：",
        "易混词辨析：",
        "絮音记忆锚点：",
    ],
)
def test_validator_rejects_model_written_expansion(forbidden: str) -> None:
    output = "\n".join(
        [
            "**setup**",
            "🔤 音标：/ˈsetʌp/",
            "**1.** n. 设置；安排；装置",
            forbidden,
        ]
    )
    rc, stderr = _validate(output, "en_to_zh")
    assert rc != 0
    assert stderr


@pytest.mark.parametrize(
    ("mode", "query"),
    [
        ("en_to_zh", "zzzznotaword"),
        ("zh_to_en", "不存在的中文词"),
    ],
)
def test_not_found_is_script_controlled_friendly_output(mode: str, query: str) -> None:
    result = _lookup_result(mode, query)
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.strip() == f"📖 '{query}' 这个词/短语暂时不在我的词典库中呢"
    rc, stderr = _validate(result.stdout, mode)
    assert rc == 0, stderr


def test_zh_to_en_does_not_match_substrings_inside_unknown_query() -> None:
    result = _lookup_result("zh_to_en", "火星词条不存在")
    assert result.returncode == 0
    assert result.stdout.strip() == "📖 '火星词条不存在' 这个词/短语暂时不在我的词典库中呢"
    assert "absence" not in result.stdout


def test_default_cli_call_returns_strict_text_for_english_word() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "dict_lookup.py"),
            "trace",
            "--mode",
            "en_to_zh",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert result.stdout.startswith("**trace**")
    assert not result.stdout.lstrip().startswith("{")
    rc, stderr = _validate(result.stdout, "en_to_zh")
    assert rc == 0, stderr


def test_bare_cli_call_infers_english_lookup_and_returns_strict_text() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "dict_lookup.py"),
            "trace",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert result.stdout.startswith("**trace**")
    rc, stderr = _validate(result.stdout, "en_to_zh")
    assert rc == 0, stderr
