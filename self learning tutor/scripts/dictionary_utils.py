#!/usr/bin/env python3
"""Shared helpers for the self-learning-tutor dictionary tools."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

POS_TOKEN_RE = re.compile(r"^[a-z]{1,12}\.", re.IGNORECASE)
POS_SEPARATOR_RE = re.compile(r"^\s*(?:[/,，、;；&·\-]|\band\b|\bor\b)?\s*", re.IGNORECASE)
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


def coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [normalize_query(str(item).strip()) for item in value]
        return "；".join(part for part in parts if part)
    return normalize_query(str(value).strip())


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
        elif text.startswith(cue):
            text = text[len(cue):].strip()
    return text


def normalize_zh_term(text: str) -> str:
    text = normalize_query(text)
    text = NUMBER_PREFIX_RE.sub("", text)
    text = strip_pos_prefix(text)
    text = text.strip(" \t\r\n。．.，,；;:：")
    text = re.sub(r"[（(][^()（）]*[)）]$", "", text).strip()
    return text


def split_pos_prefix(value: Any) -> tuple[list[str], str]:
    text = coerce_text(value)
    if not text:
        return [], ""

    cursor = text
    tokens: list[str] = []
    seen: set[str] = set()

    while cursor:
        match = POS_TOKEN_RE.match(cursor)
        if not match:
            break

        token = match.group(0).lower()
        if token not in seen:
            seen.add(token)
            tokens.append(token)

        cursor = cursor[match.end():]
        separator = POS_SEPARATOR_RE.match(cursor)
        if not separator:
            break
        cursor = cursor[separator.end():]

    if not tokens:
        return [], text
    return tokens, cursor.lstrip()


def strip_pos_prefix(value: Any) -> str:
    _, remainder = split_pos_prefix(value)
    return remainder


def extract_pos_from_text(value: Any) -> str:
    tokens, _ = split_pos_prefix(value)
    return " / ".join(tokens)


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
        text = strip_pos_prefix(text)
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


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_json_list_field(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            return [text]
        if isinstance(loaded, list):
            return loaded
        if isinstance(loaded, dict):
            return [loaded]
        return []
    return []


def record_to_entry(record: Mapping[str, Any] | Any) -> dict[str, Any]:
    word = normalize_query(_safe_str(_record_get(record, "word")))
    pos = coerce_text(_record_get(record, "pos"))
    phonetic = normalize_query(_safe_str(_record_get(record, "phonetic")))
    phonetic_uk = normalize_query(_safe_str(_record_get(record, "phonetic_uk") or phonetic))
    phonetic_us = normalize_query(_safe_str(_record_get(record, "phonetic_us") or phonetic))
    definition = _safe_str(_record_get(record, "definition"))
    translation = _safe_str(_record_get(record, "translation"))
    if not pos:
        pos = extract_pos_from_text(definition) or extract_pos_from_text(translation)
    definitions = parse_definitions(
        _record_get(record, "definitions", translation or definition)
    )
    if not definitions:
        definitions = parse_definitions(definition)
    example = ""
    for key in (
        "example",
        "sentence",
        "example_sentence",
        "sentence_en",
        "example_en",
        "sentence_text",
    ):
        example = coerce_text(_record_get(record, key, ""))
        if example:
            break
    example_source = coerce_text(_record_get(record, "example_source", ""))
    example_url = coerce_text(_record_get(record, "example_url", ""))
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
        "translation": translation,
        "definitions": definitions,
        "example": example,
        "example_source": example_source,
        "example_url": example_url,
        "idioms": parse_json_list_field(_record_get(record, "idioms")),
        "collocations": parse_json_list_field(_record_get(record, "collocations")),
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
