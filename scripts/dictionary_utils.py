#!/usr/bin/env python3
"""Shared helpers for the self-learning-tutor dictionary tools."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

POS_PREFIX_RE = re.compile(r"^(?:[a-z]{1,8}\.)+\s*", re.IGNORECASE)
NUMBER_PREFIX_RE = re.compile(r"^\s*(?:\d+|[一二三四五六七八九十]+)[.)、]\s*")
BRACKET_PREFIX_RE = re.compile(r"^\[[^\]]+\]\s*")
EN_LOOKUP_CUES = (
    "是什么意思",
    "的意思",
    "啥意思",
    "什么意思",
    "怎么读",
    "怎么写",
    "怎么念",
)
ZH_LOOKUP_CUES = (
    "英语怎么说",
    "英文怎么说",
    "翻译成英语",
    "翻译成英文",
    "用英语",
    "英文",
)
SPLIT_RE = re.compile(r"[\n；;，,、/|]+")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def normalize_query(text: str) -> str:
    return normalize_whitespace(text)


def normalize_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def strip_lookup_cues_en(text: str) -> str:
    text = normalize_query(text)
    for cue in EN_LOOKUP_CUES:
        if text.endswith(cue):
            text = text[: -len(cue)].strip()
    return text


def strip_lookup_cues_zh(text: str) -> str:
    text = normalize_query(text)
    for cue in ZH_LOOKUP_CUES:
        if text.endswith(cue):
            text = text[: -len(cue)].strip()
    return text


def normalize_zh_term(text: str) -> str:
    text = normalize_query(text)
    text = NUMBER_PREFIX_RE.sub("", text)
    text = POS_PREFIX_RE.sub("", text)
    text = text.strip(" \t\r\n。．.，,；;:：")
    text = re.sub(r"[（(][^()（）]*[)）]$", "", text).strip()
    return text


def parse_definitions(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        text = text.replace("\\n", "\n").replace("\\r", "\r")
        if text.startswith("[") and text.endswith("]"):
            try:
                loaded = json.loads(text)
            except json.JSONDecodeError:
                loaded = None
            if isinstance(loaded, list):
                raw_items = loaded
            else:
                raw_items = SPLIT_RE.split(text)
        else:
            raw_items = SPLIT_RE.split(text)
    else:
        raw_items = [str(value)]

    results: list[str] = []
    for item in raw_items:
        if item is None:
            continue
        text = normalize_query(str(item))
        if not text:
            continue
        text = NUMBER_PREFIX_RE.sub("", text)
        text = POS_PREFIX_RE.sub("", text)
        text = BRACKET_PREFIX_RE.sub("", text)
        text = text.strip(" \t\r\n。．.，,；;:：")
        text = re.sub(r"[（(][^()（）]*[)）]$", "", text).strip()
        if text:
            results.append(text)
    return results


def build_reverse_terms(definitions: list[str] | None = None, zh_terms: list[str] | None = None) -> list[str]:
    source_terms = zh_terms if zh_terms else definitions or []
    results: list[str] = []
    seen: set[str] = set()

    for item in source_terms:
        if item is None:
            continue
        for raw_piece in SPLIT_RE.split(str(item)):
            candidate = normalize_zh_term(raw_piece)
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            results.append(candidate)
    return results


def _record_get(record: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    if hasattr(record, "keys") and key in record.keys():
        return record[key]
    return default


def record_to_entry(record: Mapping[str, Any] | Any) -> dict[str, Any]:
    word = normalize_query(str(_record_get(record, "word", "")).strip())
    pos = normalize_query(str(_record_get(record, "pos", "")).strip())
    phonetic = normalize_query(str(_record_get(record, "phonetic", "")).strip())
    phonetic_uk = normalize_query(str(_record_get(record, "phonetic_uk", phonetic)).strip())
    phonetic_us = normalize_query(str(_record_get(record, "phonetic_us", phonetic)).strip())
    definition = str(_record_get(record, "definition", "")).strip()
    translation = str(_record_get(record, "translation", "")).strip()
    definitions = parse_definitions(
        _record_get(record, "definitions", translation or definition)
    )
    if not definitions:
        definitions = parse_definitions(definition)
    example = normalize_query(str(_record_get(record, "example", _record_get(record, "sentence", ""))).strip())
    example_source = normalize_query(str(_record_get(record, "example_source", "")).strip())
    example_url = normalize_query(str(_record_get(record, "example_url", "")).strip())
    source = normalize_query(str(_record_get(record, "source", "ecdict")).strip()) or "ecdict"
    collins = normalize_int(_record_get(record, "collins", 0))
    oxford = normalize_int(_record_get(record, "oxford", 0))
    bnc = normalize_int(_record_get(record, "bnc", 0))
    frq = normalize_int(_record_get(record, "frq", _record_get(record, "frequency", 0)))
    frequency = frq or bnc or normalize_int(_record_get(record, "frequency", 0))
    tag = normalize_query(str(_record_get(record, "tag", "")).strip())
    exchange = normalize_query(str(_record_get(record, "exchange", "")).strip())
    detail = str(_record_get(record, "detail", "")).strip()
    audio = normalize_query(str(_record_get(record, "audio", "")).strip())
    zh_terms = _record_get(record, "zh_terms")
    if isinstance(zh_terms, str):
        try:
            loaded = json.loads(zh_terms)
        except json.JSONDecodeError:
            loaded = None
        zh_terms = loaded if isinstance(loaded, list) else [zh_terms]
    elif zh_terms is None:
        zh_terms = []

    return {
        "word": word,
        "pos": pos,
        "phonetic_uk": phonetic_uk,
        "phonetic_us": phonetic_us,
        "phonetic": phonetic or phonetic_us or phonetic_uk,
        "definition": definition,
        "translation": translation,
        "definitions": definitions,
        "example": example,
        "example_source": example_source,
        "example_url": example_url,
        "source": source,
        "collins": collins,
        "oxford": oxford,
        "tag": tag,
        "bnc": bnc,
        "frq": frq,
        "exchange": exchange,
        "detail": detail,
        "audio": audio,
        "frequency": frequency,
        "zh_terms": build_reverse_terms(definitions, zh_terms),
    }
