#!/usr/bin/env python3
"""Build gaokao_phrases.json from multiple authoritative sources.

Sources:
  A) 2ndLA/english-phrases senior.txt (2808 raw phrases, coverage)
  B) zizzs.com 236 high-frequency PDF (Chinese definitions + ranking)
  C) maimemo-export CSV (Chinese translations from crowdsourced learner data)
  D) Existing seed entries (43 manually curated)

Output: gaokao_phrases.json compatible with dict_lookup.py + validate_lookup_output.py

Usage:
    python3 scripts/build_phrase_db.py --output data/gaokao_phrases.json
    python3 scripts/build_phrase_db.py --output data/gaokao_phrases.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_A_URL = (
    "https://raw.githubusercontent.com/2ndLA/english-phrases/main/lists/senior.txt"
)
SOURCE_C_CSV_URL = (
    "https://raw.githubusercontent.com/busiyiworld/maimemo-export"
    "/main/exported/translation/%E5%88%9D%E4%B8%AD%E8%8B%B1%E8%AF%AD%E5%B8%B8%E8%80%83%E7%9F%AD%E8%AF%AD.csv"
)

PREPOSITIONS = frozenset({
    "about", "above", "across", "after", "against", "along", "among",
    "around", "at", "before", "behind", "below", "beneath", "beside",
    "between", "beyond", "by", "down", "during", "except", "for",
    "from", "in", "inside", "into", "like", "near", "of", "off",
    "on", "onto", "out", "outside", "over", "past", "round", "since",
    "through", "throughout", "till", "to", "toward", "towards", "under",
    "until", "up", "upon", "with", "within", "without",
})

PHRASAL_VERB_BASES = frozenset({
    "break", "bring", "call", "carry", "come", "cut", "get", "give",
    "go", "hold", "keep", "look", "make", "pick", "pull", "put", "run",
    "set", "take", "turn", "work",
})

PARTICLES_PREPS = frozenset({
    "away", "back", "down", "for", "in", "off", "on", "out", "over",
    "round", "through", "to", "up", "with", "across", "along", "ahead",
    "apart", "aside", "behind", "by", "forward", "into", "of", "after",
    "at",
})

KNOWN_FIXED = frozenset({
    "as soon as possible", "by the way", "in fact", "at first", "at last",
    "from now on", "so far", "right now", "of course", "at least", "at once",
    "in time", "on time", "no longer", "at present", "in general",
})

# Multi-word prepositional openers not in PREPOSITIONS set
EXTRA_PREPOSITIONAL_OPENERS = frozenset({
    "instead", "according", "due", "owing", "regarding", "concerning",
    "despite", "except", "nearby", "opposite", "round", "via",
    "because",
})

KNOWN_IDIOMS = frozenset({
    "break the ice", "piece of cake", "cost an arm and a leg",
    "under the weather", "hot potato", "once in a blue moon",
    "hit the nail on the head", "let the cat out of the bag",
    "spill the beans", "burn the midnight oil",
})

# ---------------------------------------------------------------------------
# Phrase normalization
# ---------------------------------------------------------------------------

_VARIANT_RE = re.compile(
    r"(?<=\s)sb\.?(?=\s|$)"       # sb or sb. as standalone token
    r"|(?<=\s)sth\.?(?=\s|$)"     # sth or sth. as standalone token
    r"|\s+\.{2,3}"                  # ellipsis ...
    r"|…+"                          # unicode ellipsis … (U+2026)
    r"|['’]s(?=\s|$)"              # ‘s possessive (straight + smart quote)
)

# Post-normalization noise filter patterns
_ELLIPSIS_RE = re.compile(r"\.{2,3}|…+")  # any remaining ellipsis
_MAX_WORDS = 6  # drop phrases longer than this (real idioms added manually as seeds)

# Common short words that get glued to preceding words in source data
_GLUE_WORDS = frozenset({
    "for", "and", "but", "the", "off", "out", "up", "on", "in",
    "at", "to", "by", "of", "as", "is", "it", "or", "if", "no", "so",
    "one", "all", "me", "my", "we", "us",
})

# Real English words that look like [prefix]+[glue_word] but must NOT be split.
_NO_SPLIT = frozenset({
    "into", "onto", "upon", "without", "within", "throughout",
})

# Known word stems that can legitimately appear before a merged glue word.
# This allowlist prevents false positives like action→acti+on, prison→pris+on.
_SPLIT_PREFIXES = frozenset(
    PHRASAL_VERB_BASES
    | PREPOSITIONS
    | {
        # Common verbs/adjectives that may merge with particles in source data
        "be", "do", "have", "say", "think", "want", "need", "try", "use",
        "let", "help", "start", "stop", "play", "move", "live", "stand",
        "fall", "drop", "fill", "check", "clean", "clear", "close", "point",
        "pay", "wait", "ask", "answer", "believe", "depend", "base",
        "switch", "cross", "pass", "push", "show", "tell", "write",
        "read", "find", "lose", "win", "buy", "sell", "send", "build",
        "catch", "throw", "draw", "drive", "fly", "grow", "hear", "lead",
        "lie", "mean", "meet", "ring", "rise", "sit", "speak",
        "stay", "talk", "walk", "wake", "make", "get", "give",
        "take", "come", "go", "look", "put", "set", "turn", "work",
        "bring", "carry", "call", "cut", "hold", "keep", "pick", "pull",
        "break", "point", "head", "hand", "face", "back", "way",
    }
)


def normalize_phrase(raw: str) -> str:
    text = raw.strip().lower()
    text = _VARIANT_RE.sub("", text)
    # Split merged words at word level (avoid substring false positives)
    text = _split_merged_words(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_merged_words(text: str) -> str:
    """Split glued words like 'takefor'->'take for', 'putin'->'put in',
    'look onas'->'look on as'.

    Only splits when the suffix is a glue word AND the prefix is a known
    valid word stem (from _SPLIT_PREFIXES). This avoids false positives on
    real English words like 'action', 'prison', 'forward'.
    """
    words = text.split()
    result: list[str] = []
    for w in words:
        # Try longest glue-word suffix first to avoid greedy short matches
        split = _try_split_word(w)
        if split:
            result.extend(split)
        else:
            result.append(w)
    return " ".join(result)


def _try_split_word(w: str) -> list[str] | None:
    """If *w* is two known words glued together, return [prefix, suffix].

    Returns None if *w* should be kept as-is.
    """
    # Never split real compound words
    if w in _NO_SPLIT:
        return None
    # Sort glue words by length descending so we try longer matches first
    for gw in sorted(_GLUE_WORDS, key=len, reverse=True):
        if w.endswith(gw) and len(w) > len(gw) + 1:
            prefix = w[: -len(gw)]
            if prefix in _SPLIT_PREFIXES:
                return [prefix, gw]
    return None



def should_keep_phrase(phrase: str) -> bool:
    if not phrase or not phrase.strip():
        return False
    words = phrase.split()
    # Single-word entries are template fragments, not real phrases
    if len(words) < 2:
        return False
    # Any remaining ellipsis means it's a template pattern like "accuse…of…"
    if _ELLIPSIS_RE.search(phrase):
        return False
    # Drop overly long entries (likely concatenation garbage)
    if len(words) > _MAX_WORDS:
        return False
    return True


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_phrase(phrase: str) -> str:
    words = phrase.split()
    if not words:
        return "collocation"
    first = words[0]

    # Known idioms
    if phrase in KNOWN_IDIOMS:
        return "idiom"

    # Known fixed expressions
    if phrase in KNOWN_FIXED:
        return "fixed_expression"

    # be + adj/pp = collocation (adjective collocation)
    if first == "be" and len(words) >= 3:
        return "collocation"

    # Preposition-first = prepositional phrase
    if first in PREPOSITIONS or first in EXTRA_PREPOSITIONAL_OPENERS:
        return "prepositional_phrase"

    # Common phrasal verb base + particle/prep
    if first in PHRASAL_VERB_BASES and len(words) <= 5:
        last = words[-1] if len(words) > 1 else ""
        if last in PARTICLES_PREPS:
            return "phrasal_verb"

    # Default: collocation
    return "collocation"


# ---------------------------------------------------------------------------
# Frequency assignment
# ---------------------------------------------------------------------------


def assign_frequency(
    rank_236: int | None = None,
    source_count: int = 1,
) -> int:
    base = 3
    if rank_236 is not None:
        if rank_236 <= 50:
            base = 5
        elif rank_236 <= 150:
            base = 4
        else:
            base = 3
    # Multi-source boost (capped at 5)
    freq = min(base + max(0, source_count - 1), 5)
    return freq


# ---------------------------------------------------------------------------
# Chinese term extraction for reverse index
# ---------------------------------------------------------------------------


def extract_zh_terms(definitions: list[str], max_terms: int = 3) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for d in definitions:
        # Split by common delimiters
        for part in re.split(r"[；;、，,\s]+", d):
            part = part.strip()
            # Strip prefix like "phr.", "adj.", "v.", "n."
            part = re.sub(r"^(?:phr\.|adj\.|v\.|n\.|adv\.|prep\.)\s*", "", part)
            if not part:
                continue
            # Extract Chinese terms (filter short ones and non-Chinese)
            chinese_parts = re.findall(r"[一-鿿]{2,}", part)
            for cp in chinese_parts:
                if cp not in seen:
                    seen.add(cp)
                    terms.append(cp)
                    if len(terms) >= max_terms:
                        return terms
    return terms


# ---------------------------------------------------------------------------
# Seed data loader
# ---------------------------------------------------------------------------


def load_seed_data() -> list[dict]:
    seed_path = ROOT / "data" / "gaokao_phrases.json"
    if not seed_path.exists():
        return []
    data = json.loads(seed_path.read_text("utf-8"))
    return data.get("phrases", [])


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------


def merge_phrases(
    source_a: list[str],
    source_b: dict[str, dict],
    source_c: dict[str, list[str]],
    seeds: list[dict],
) -> list[dict]:
    merged: dict[str, dict] = {}

    # 1. Load seeds first (highest priority for examples/definitions)
    for entry in seeds:
        key = normalize_phrase(entry["phrase"])
        if key and key not in merged:
            merged[key] = {
                "phrase": key,
                "category": entry.get("category", "collocation"),
                "definitions": list(entry.get("definitions", [])),
                "examples": list(entry.get("examples", [])),
                "zh_terms": list(entry.get("zh_terms", [])),
                "frequency": entry.get("frequency", 3),
                "sources": ["seed"],
                "rank_236": None,
            }

    # 2. Add Source A phrases (coverage)
    for raw in source_a:
        key = normalize_phrase(raw)
        if not key:
            continue
        if key not in merged:
            cat = classify_phrase(key)
            merged[key] = {
                "phrase": key,
                "category": cat,
                "definitions": [],
                "examples": [],
                "zh_terms": [],
                "frequency": 3,
                "sources": ["source_a"],
                "rank_236": None,
            }
        else:
            if "source_a" not in merged[key]["sources"]:
                merged[key]["sources"].append("source_a")

    # 3. Enrich with Source B (ranked definitions)
    for key, info in source_b.items():
        norm_key = normalize_phrase(key)
        if not norm_key:
            continue
        if norm_key in merged:
            entry = merged[norm_key]
            if "source_b" not in entry["sources"]:
                entry["sources"].append("source_b")
            if info.get("rank") is not None:
                entry["rank_236"] = info["rank"]
            for defn in info.get("definitions", []):
                if defn not in entry["definitions"]:
                    entry["definitions"].append(defn)
        else:
            cat = classify_phrase(norm_key)
            merged[norm_key] = {
                "phrase": norm_key,
                "category": cat,
                "definitions": list(info.get("definitions", [])),
                "examples": [],
                "zh_terms": [],
                "frequency": 3,
                "sources": ["source_b"],
                "rank_236": info.get("rank"),
            }

    # 4. Enrich with Source C (CSV translations)
    for key, defs in source_c.items():
        norm_key = normalize_phrase(key)
        if not norm_key:
            continue
        if norm_key in merged:
            entry = merged[norm_key]
            if "source_c" not in entry["sources"]:
                entry["sources"].append("source_c")
            for d in defs:
                if d not in entry["definitions"]:
                    entry["definitions"].append(d)

    # 5. Finalize: compute frequency, zh_terms, clean up, filter noise
    result: list[dict] = []
    dropped = 0
    for key, entry in merged.items():
        # Filter noise: drop template fragments, ellipsis remnants, overlong entries
        if not should_keep_phrase(key):
            dropped += 1
            continue
        entry["frequency"] = assign_frequency(
            rank_236=entry.get("rank_236"),
            source_count=len(entry.get("sources", [])),
        )
        entry["zh_terms"] = extract_zh_terms(entry.get("definitions", []))
        # Remove internal tracking fields
        entry.pop("sources", None)
        entry.pop("rank_236", None)
        result.append(entry)

    if dropped:
        print(f"[Filter] Dropped {dropped} noise entries")

    return result


# ---------------------------------------------------------------------------
# Card formatting (compatible with validate_lookup_output.py)
# ---------------------------------------------------------------------------


def format_card_en_to_zh(entry: dict) -> str:
    """Format a phrase/word entry as en_to_zh lookup card."""
    lines: list[str] = [f"**{entry['phrase']}**"]

    phonetic = entry.get("phonetic")
    if phonetic:
        lines.append(f"- 🔤 音标：{phonetic}")

    for i, d in enumerate(entry.get("definitions", [])[:2], 1):
        label = f"- 🇨🇳 释义：" if i == 1 else f"- 🇨🇳 释义 {i}："
        lines.append(f"{label}{d}")

    examples = entry.get("examples", [])
    if examples:
        ex = examples[0]
        lines.append(f"- 💬 例句：{ex['en']}（{ex['zh']}）")

    return "\n".join(lines)


def format_card_zh_to_en(entry: dict, query: str) -> str:
    """Format a phrase/word entry as zh_to_en lookup card."""
    lines: list[str] = [f"**{query}**"]
    phonetic = entry.get("phonetic")
    lines.append(f"- 🔤 最常用英文：{entry['phrase']}" + (f" {phonetic}" if phonetic else ""))

    if phonetic:
        lines.append(f"- 🔤 音标：{phonetic}")

    for i, d in enumerate(entry.get("definitions", [])[:2], 1):
        label = f"- 🇨🇳 对应义：" if i == 1 else f"- 🇨🇳 对应义 {i}："
        lines.append(f"{label}{d}")

    examples = entry.get("examples", [])
    if examples:
        ex = examples[0]
        lines.append(f"- 💬 例句：{ex['en']}（{ex['zh']}）")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output builder
# ---------------------------------------------------------------------------


def build_output(phrases: list[dict]) -> dict:
    categories = Counter(p["category"] for p in phrases)
    with_def = sum(1 for p in phrases if p.get("definitions"))
    with_ex = sum(1 for p in phrases if p.get("examples"))

    return {
        "version": "2.0",
        "description": "高考英语核心词组/短语（三源交叉验证版）",
        "sources": [
            "2ndLA/senior.txt(2808)",
            "zizzs-236-PDF(891)",
            "maimemo-csv(~800)",
            "seed-manual(43)",
        ],
        "stats": {
            "total": len(phrases),
            "categories": dict(categories),
            "with_definitions": with_def,
            "with_examples": with_ex,
        },
        "phrases": phrases,
    }


# ---------------------------------------------------------------------------
# Source A loader
# ---------------------------------------------------------------------------


def load_source_a() -> list[str]:
    """Download and parse 2ndLA senior.txt (2808 raw phrases)."""
    print(f"[Source A] Downloading {SOURCE_A_URL} ...")
    try:
        resp = urlopen(SOURCE_A_URL, timeout=30)
        raw = resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError) as e:
        print(f"[Source A] WARNING: download failed ({e}), trying local cache ...")
        cached = ROOT / "data" / "_cache_senior.txt"
        if cached.exists():
            raw = cached.read_text("utf-8")
        else:
            print(f"[Source A] ERROR: no cache found at {cached}")
            sys.exit(1)
    lines = [normalize_phrase(line) for line in raw.splitlines() if line.strip()]
    (ROOT / "data" / "_cache_senior.txt").write_text("\n".join(lines), "utf-8")
    print(f"[Source A] Loaded {len(lines)} phrases")
    return lines


# ---------------------------------------------------------------------------
# Source B: 236 high-frequency phrases (pre-extracted from PDF)
# ---------------------------------------------------------------------------

_PDF_ENTRIES: dict[str, tuple[int, str]] = {
    "abide by": (1, "忠于；遵守"),
    "be absent from": (2, "缺席，不在"),
    "absence of mind": (3, "心不在焉"),
    "be absorbed in": (4, "全神贯注于"),
    "(be) abundant in": (5, "富于；富有"),
    "access to": (6, "能接近；进入；了解"),
    "by accident": (7, "偶然地；意外"),
    "of one's own accord": (8, "自愿地；主动地"),
    "in accord with": (9, "与…一致"),
    "with one accord": (10, "一致地"),
    "in accordance with": (11, "依照；根据"),
    "on one's own account": (12, "为了某人的缘故"),
    "account for": (13, "总计；等于；解释"),
    "amount to": (14, "总计；等于"),
    "answer for": (15, "对…负责"),
    "answer to": (16, "适合；符合"),
    "be anxious about": (17, "为…焦急不安"),
    "apologize to sb for sth": (18, "为…向某人道歉"),
    "appeal to sb for sth": (19, "为某事向某人呼吁"),
    "appeal to sb": (20, "对某人有吸引力"),
    "apply for": (21, "申请；请求"),
    "apply oneself to": (22, "专心于"),
    "apply to": (23, "应用；适用于"),
    "approve of": (24, "赞成；同意"),
    "arise from": (25, "由…产生；由…引起"),
    "arm in arm": (26, "臂挽臂地"),
    "around the corner": (27, "即将到来；在附近"),
    "arrive at": (28, "到达；达成"),
    "as a consequence": (29, "因此；结果"),
    "as a result": (30, "因此；结果"),
    "as a rule": (31, "通常；一般说来"),
    "as far as": (32, "就…而言；远到"),
    "as follows": (33, "如下"),
    "as for": (34, "至于；关于"),
    "as good as": (35, "和…几乎一样"),
    "in agreement with": (36, "同意；一致"),
    "ahead of": (37, "在…之前；超过"),
    "ahead of time": (38, "提前"),
    "in the air": (39, "不肯定；在谣传中"),
    "above all": (40, "尤其是；最重要的"),
    "in all": (41, "总共；总计"),
    "after all": (42, "毕竟；到底"),
    "all at once": (43, "突然"),
    "once and for all": (44, "只此一次；彻底地"),
    "first of all": (45, "首先"),
    "all in all": (46, "大体上说；总而言之"),
    "allow for": (47, "考虑到；估计到"),
    "answer for": (49, "对…负责"),
    "appeal to": (50, "呼吁；吸引"),
    "arrive at": (52, "到达；达成"),
    "ask after": (53, "问候；询问"),
    "ask for": (54, "请求；要求"),
    "assist in": (55, "帮助；协助"),
    "aim at": (56, "瞄准；旨在"),
    "all alone": (57, "独自一人"),
    "all along": (58, "始终；一直"),
    "all around": (59, "到处；四周"),
    "all but": (60, "几乎；除了…都"),
    "all of a sudden": (61, "突然"),
    "all out": (62, "全力以赴"),
    "all over": (63, "到处；结束"),
    "all right": (64, "好的；顺利"),
    "all the same": (65, "仍然；照样"),
    "all the way": (66, "一路上；自始至终"),
    "all together": (67, "同时；总共"),
    "apart from": (68, "除…外；且不说"),
    "as a matter of fact": (69, "事实上；其实"),
    "as a result of": (70, "由于…的结果"),
    "as if": (71, "好像；仿佛"),
    "as it is": (72, "实际上；既然如此"),
    "as it were": (73, "可以说；某种程度上"),
    "as long as": (74, "只要"),
    "as soon as": (75, "一…就…"),
    "as though": (76, "好像；仿佛"),
    "as to": (77, "关于；至于"),
    "as usual": (78, "像往常一样"),
    "as well": (79, "也；同样"),
    "as well as": (80, "既…又…；此外"),
    "aside from": (81, "除…外"),
    "at a distance": (82, "在一定距离处"),
    "at a loss": (83, "困惑；不知所措"),
    "at all": (84, "根本；究竟"),
    "at all costs": (85, "不惜任何代价"),
    "at all events": (86, "无论如何"),
    "at any rate": (87, "无论如何"),
    "at best": (88, "最多；最好也不过"),
    "at ease": (89, "自在；安心"),
    "at first": (90, "起初；首先"),
    "at first sight": (91, "乍一看；初见时"),
    "at hand": (92, "在手边；即将到来"),
    "at heart": (93, "内心里；本质上"),
    "at home": (94, "在家；自在"),
    "at intervals": (95, "不时；每隔…"),
    "at large": (96, "详尽地；逍遥法外"),
    "at last": (97, "终于；最后"),
    "at least": (98, "至少"),
    "at length": (99, "最后；详细地"),
    "at most": (100, "最多"),
    "at no time": (101, "决不；从不"),
    "at once": (102, "立刻；同时"),
    "at one time": (103, "曾经；同时"),
    "at present": (104, "目前；现在"),
    "at random": (105, "随机地；任意地"),
    "at risk": (106, "处于危险中"),
    "at sight": (107, "一见就…"),
    "at table": (108, "在桌边；在进餐"),
    "at that time": (109, "在那时"),
    "at the age of": (110, "在…岁时"),
    "at the beginning": (111, "起初；开始时"),
    "at the bottom of": (112, "在…底部"),
    "at the cost of": (113, "以…为代价"),
    "at the end of": (114, "在…末端"),
    "at the expense of": (115, "以…为代价"),
    "at the front of": (116, "在…前面"),
    "at the latest": (117, "最迟"),
    "at the moment": (118, "此刻；现在"),
    "at the most": (119, "最多"),
    "at the risk of": (120, "冒…的风险"),
    "at the start of": (121, "在…开始时"),
    "at times": (122, "有时；不时"),
    "at work": (123, "在工作；在运转"),
    "attach importance to": (124, "重视"),
    "attach to": (125, "附上；依恋"),
    "attempt to do sth": (126, "试图做某事"),
    "attend on": (127, "照料；侍候"),
    "attend to": (128, "注意；处理"),
    "attitude to": (129, "对…的态度"),
    "attract attention to": (130, "引起对…的注意"),
    "attribute to": (131, "归因于；认为是"),
    "avoid doing sth": (132, "避免做某事"),
    "awake to": (133, "意识到；觉醒到"),
    "back and forth": (134, "来回地；反复地"),
    "back away": (135, "后退；退缩"),
    "back up": (136, "支持；备份"),
    "bargain for": (137, "讨价还价；指望"),
    "bargain with": (138, "与…讨价还价"),
    "base on": (139, "以…为基础；基于"),
    "based on": (140, "以…为基础；基于"),
    "be able to": (141, "能够；有能力"),
    "be about to": (142, "即将；正要"),
    "be absorbed in": (143, "全神贯注于"),
    "be accustomed to": (144, "习惯于"),
    "be acquainted with": (145, "熟悉；认识"),
    "be addicted to": (146, "沉迷于；嗜好"),
    "be afraid of": (147, "害怕；恐惧"),
    "be angry at": (148, "生气；愤怒"),
    "be anxious about": (149, "焦虑；担心"),
    "be anxious to": (150, "渴望；急于"),
    "be ashamed of": (151, "感到羞愧"),
    "be associated with": (152, "与…有关联"),
    "be aware of": (153, "意识到；知道"),
    "be based on": (154, "以…为基础"),
    "be bound to": (155, "必定；一定要"),
    "be busy doing": (156, "忙于做"),
    "be busy with": (157, "忙于"),
    "be capable of": (158, "有能力；能够"),
    "be concerned about": (159, "关心；挂念"),
    "be concerned with": (160, "与…有关"),
    "be connected with": (161, "与…相连"),
    "be content with": (162, "满足于；对…满意"),
    "be crazy about": (163, "热衷于；迷恋"),
    "be curious about": (164, "好奇；想知道"),
    "be different from": (165, "不同于；与…不同"),
    "be eager for": (166, "渴望；热切希望"),
    "be equal to": (167, "等于；胜任"),
    "be exposed to": (168, "暴露于；接触"),
    "be faced with": (169, "面对；面临"),
    "be familiar to": (170, "为…所熟悉"),
    "be familiar with": (171, "熟悉；通晓"),
    "be famous for": (172, "因…而著名"),
    "be fed up with": (173, "厌倦；受够了"),
    "be fit for": (174, "适合；胜任"),
    "be fond of": (175, "喜欢；喜爱"),
    "be good at": (176, "擅长；善于"),
    "be hard on": (177, "对…严厉；苛刻"),
    "be interested in": (178, "对…感兴趣"),
    "be known as": (179, "被称为；被认为是"),
    "be known for": (180, "因…而闻名"),
    "be late for": (181, "迟到"),
    "be likely to": (182, "可能；很可能"),
    "be located in": (183, "位于；坐落在"),
    "be lost": (184, "迷失；丢失"),
    "be lost in": (185, "沉浸于；迷失在"),
    "be off duty": (186, "下班"),
    "be on duty": (187, "上班；值班"),
    "be out of": (188, "缺；用完"),
    "be out of practice": (189, "荒疏；生疏"),
    "be out of touch": (190, "失去联系"),
    "be particular about": (191, "讲究；挑剔"),
    "be pleased with": (192, "对…满意"),
    "be popular with": (193, "受…欢迎；流行"),
    "be proud of": (194, "为…感到骄傲"),
    "be ready for": (195, "准备好"),
    "be related to": (196, "与…相关"),
    "be relevant to": (197, "与…相关；有关"),
    "be responsible for": (198, "对…负责；是…的原因"),
    "be rich in": (199, "富有；富含"),
    "be satisfied with": (200, "对…满意"),
    "be scared to death": (201, "吓死；恐惧至极"),
    "be short of": (202, "缺少；短缺"),
    "be similar to": (203, "相似；类似"),
    "be strict with": (204, "对…严格；严厉"),
    "be supposed to": (205, "应该；被期望"),
    "be sure of": (206, "确信；肯定"),
    "be sure to": (207, "务必；一定"),
    "be tired from": (208, "因…而疲劳"),
    "be tired of": (209, "厌倦；厌烦"),
    "be true of": (210, "适用于；符合于"),
    "be used to doing": (211, "习惯于做"),
    "be willing to": (212, "愿意；乐意"),
    "bear in mind": (213, "记住；考虑到"),
    "because of": (214, "因为；由于"),
    "before long": (215, "不久；很快"),
    "begin with": (216, "以…开始"),
    "believe in": (217, "相信；信任"),
    "belong to": (218, "属于；归于"),
    "benefit from": (219, "受益于；从…获益"),
    "best of all": (220, "最好的是；尤其"),
    "beyond control": (221, "无法控制；失控"),
    "beyond one's reach": (222, "够不着；力不能及"),
    "beyond repair": (223, "无法修理；报废"),
    "bit by bit": (224, "一点一点地；逐渐地"),
    "blame for": (226, "责备；归咎于"),
    "blame sb for sth": (227, "因某事责备某人"),
    "blow out": (228, "吹灭；爆裂"),
    "blow up": (229, "爆炸；发火"),
    "boast of": (230, "自夸；吹嘘"),
    "border on": (231, "近似；接近"),
    "both and": (232, "既…又…"),
    "break away": (233, "脱离；逃脱"),
    "break down": (234, "分解；出故障；崩溃"),
    "break in": (235, "闯入；打断"),
    "break into": (236, "破门而入；突然…起来"),
    "break off": (237, "折断；中断"),
    "break out": (238, "爆发；突发"),
    "break the ice": (239, "打破僵局；破冰"),
    "break through": (240, "突破；突围"),
    "break up": (241, "破碎；解散；分手"),
    "bring about": (242, "引起；导致"),
    "bring back": (243, "带回；使回忆起"),
    "bring down": (244, "降低；击落"),
    "bring forward": (245, "提出；提前"),
    "bring in": (246, "引进；收获"),
    "bring into effect": (247, "使生效；实施"),
    "bring out": (248, "出版；生产；阐明"),
    "bring up": (249, "抚养；提出；呕吐"),
    "build up": (250, "建立；增强；积累"),
    "burn down": (251, "烧毁；火力减弱"),
    "burn out": (252, "烧尽；耗尽"),
    "burn up": (253, "烧掉；消耗"),
    "burst into": (254, "突然…起来"),
    "but for": (255, "要不是；若无"),
    "by accident": (256, "偶然；意外"),
    "by air": (257, "乘飞机；通过航空"),
    "by all means": (258, "当然；一定"),
    "by and by": (259, "不久；迟早"),
    "by and large": (260, "大体上；总的来说"),
    "by chance": (261, "偶然；意外"),
    "by comparison": (262, "相比之下"),
    "by contrast": (263, "对比之下；相反"),
    "by far": (264, "最；…得多"),
    "by force": (265, "强行；用武力"),
    "by hand": (266, "手工；用手"),
    "by itself": (267, "独自；自动"),
    "by means of": (268, "借助于；通过"),
    "by mistake": (269, "错误地；无意中"),
    "by name": (270, "名叫；凭名字"),
    "by nature": (271, "天生；生就"),
    "by no means": (272, "决不；一点也不"),
    "by now": (273, "到现在；此刻"),
    "by oneself": (274, "单独；独自"),
    "by the way": (275, "顺便说；顺便问一下"),
    "by this means": (276, "用这种方法"),
    "call after": (277, "以…命名"),
    "call at": (278, "拜访（某地）"),
    "call back": (279, "回电话；召回"),
    "call for": (280, "要求；需要"),
    "call forth": (281, "唤起；激起"),
    "call in": (282, "召来；请来"),
    "call off": (283, "取消；转移走"),
    "call on": (284, "号召；访问"),
    "call out": (285, "大声叫喊；出动"),
    "call up": (286, "打电话；召集"),
    "calm down": (287, "平静下来；镇定"),
    "can hardly wait": (288, "迫不及待"),
    "can't help but": (289, "不得不；禁不住"),
    "can't help doing": (290, "忍不住做"),
    "care about": (291, "关心；在乎"),
    "care for": (292, "照顾；喜欢"),
    "carry away": (293, "拿走；使入迷"),
    "carry off": (294, "夺走；赢得"),
    "carry on": (295, "继续；进行"),
    "carry out": (296, "执行；贯彻；开展"),
    "catch a glimpse of": (297, "瞥见一眼"),
    "catch fire": (298, "着火"),
    "catch hold of": (299, "抓住；握住"),
    "catch on": (300, "理解；流行起来"),
    "catch one's eye": (301, "引人注目"),
    "catch sight of": (302, "看见；发现"),
    "catch up": (303, "赶上；跟上"),
    "catch up with": (304, "赶上；追上"),
    "cater for": (305, "满足需要；迎合"),
    "center on": (306, "集中于；围绕"),
    "change for": (307, "换；交换"),
    "change into": (308, "变成；兑换为"),
    "check in": (309, "办理登记手续；入住"),
    "check out": (310, "结账离开；检查"),
    "cheer up": (311, "高兴起来；振作起来"),
    "clean out": (312, "清扫干净；花光"),
    "clean up": (313, "清理；打扫；整顿"),
    "clear away": (314, "清除；收拾"),
    "clear off": (315, "离开；清理"),
    "clear out": (316, "腾空；清除"),
    "clear up": (317, "澄清；整理；放晴"),
    "close down": (318, "关闭；停工"),
    "close in": (319, "逼近；包围"),
    "close up": (320, "封闭；靠近"),
    "collect oneself": (321, "镇定；集中思想"),
    "come about": (322, "发生；产生"),
    "come across": (323, "偶遇；被发现"),
    "come along": (324, "一起来；出现"),
    "come at": (325, "攻击；冲向"),
    "come back": (326, "回来；恢复"),
    "come before": (327, "先于；比…重要"),
    "come by": (328, "得到；经过"),
    "come down": (329, "下降；流传下来"),
    "come down on": (330, "惩罚；斥责"),
    "come down to": (331, "归结为；涉及"),
    "come for": (332, "来找；来取"),
    "come forth": (333, "出现；被公布"),
    "come forward": (334, "挺身而出；自告奋勇"),
    "come from": (335, "来自；出生于"),
    "come home": (336, "回家；醒悟"),
    "come in": (337, "进来；到达；流行"),
    "come into being": (338, "形成；产生"),
    "come into effect": (339, "生效；开始实施"),
    "come into existence": (340, "形成；产生"),
    "come into possession of": (341, "占有；拥有"),
    "come into view": (342, "进入视野；被看见"),
    "come of": (343, "来自；由于"),
    "come off": (344, "离开；成功；举行"),
    "come on": (345, "快点；开始；出场"),
    "come out": (346, "出版；结果是；显露"),
    "come over": (347, "过来；顺便来访"),
    "come round": (348, "苏醒；恢复；改变主意"),
    "come straight to the point": (349, "直截了当地说"),
    "come through": (350, "经历；安然度过；传出"),
    "come to": (351, "共计；谈到；苏醒"),
    "come to a close": (352, "结束"),
    "come to a conclusion": (353, "得出结论"),
    "come to a decision": (354, "作出决定"),
    "come to an end": (355, "结束"),
    "come to life": (356, "苏醒；活跃起来"),
    "come to terms with": (357, "达成协议；接受"),
    "come to the point": (358, "说到要点"),
    "come true": (359, "实现；成为现实"),
    "come up": (360, "走近；被提出；发芽"),
    "come up against": (361, "遇到；面对"),
    "come up to": (362, "达到；等于"),
    "come up with": (363, "想出；提出"),
    "come what may": (364, "不管怎样；无论如何"),
    "common sense": (365, "常识；常理"),
    "compare to": (366, "比作；比较"),
    "compare with": (367, "与…比较"),
    "compensate for": (368, "补偿；赔偿"),
    "complain about": (369, "抱怨；投诉"),
    "complain of": (370, "诉苦；抱怨"),
    "concentrate on": (371, "集中；全神贯注"),
    "congratulate on": (372, "祝贺；恭喜"),
    "connect to": (373, "连接到；与…有关"),
    "connect with": (374, "与…连接；联系"),
    "consider as": (375, "把…看作；认为"),
    "consist in": (376, "在于；存在于"),
    "consist of": (377, "由…组成；包括"),
    "consist with": (378, "符合；一致"),
    "consult with": (379, "商量；磋商；请教"),
    "contrary to": (380, "相反；与…相对"),
    "contribute to": (381, "有助于；贡献；导致"),
    "count on": (382, "指望；依赖；信赖"),
    "cover up": (383, "掩盖；掩饰"),
    "cross off": (384, "划掉；删去"),
    "crowd in": (385, "涌入；挤进"),
    "cry down": (386, "贬低；拒绝"),
    "cry for": (387, "哭着要；急需"),
    "cry off": (388, "决定不参加；取消"),
    "cry out": (389, "大声呼喊；发出抱怨"),
    "cut across": (390, "抄近路；超越"),
    "cut back": (391, "削减；缩短"),
    "cut back on": (392, "削减；减少"),
    "cut down": (393, "砍倒；削减；删节"),
    "cut in": (394, "插嘴；超车；打断"),
    "cut into": (395, "侵犯；减少；打断"),
    "cut off": (396, "切断；中断；死亡"),
    "cut out": (397, "剪下；停止；删去"),
    "cut through": (398, "穿透；抄近路"),
    "cut up": (399, "切碎；割伤"),
    "dance to": (400, "随着…跳舞"),
    "dare to": (401, "敢；敢于"),
    "date back to": (402, "追溯到；始于"),
    "date from": (403, "追溯到；始于"),
    "day after day": (404, "日复一日"),
    "day and night": (405, "日夜不停；昼夜"),
    "day by day": (406, "一天天；逐日"),
    "deal in": (407, "经营；买卖"),
    "deal out": (408, "分配；处理"),
    "deal with": (409, "处理；对付；论述"),
    "depend on": (410, "取决于；依赖；依靠"),
    "depart from": (411, "离开；违反；出发"),
    "derive from": (412, "源于；得自；来自"),
    "descend from": (413, "起源于；是…的后代"),
    "describe as": (414, "描述为；看作"),
    "despite of": (415, "尽管；虽然"),
    "die away": (416, "渐渐消失；减弱"),
    "die down": (417, "平息；静下来"),
    "die for": (418, "为…而死；渴望"),
    "die from": (419, "死于；因…而死"),
    "die of": (420, "死于（疾病等）"),
    "die off": (421, "相继死去；绝种"),
    "die out": (422, "灭绝；消失"),
    "differ from": (423, "不同于；与…不同"),
    "dig down": (424, "挖掘；查究"),
    "dig in": (425, "掘土；钻研"),
    "dig into": (426, "钻研；探究"),
    "dig out": (427, "挖出；发现"),
    "dig up": (428, "挖出；翻找"),
    "dip into": (429, "涉猎；略看"),
    "disagree with": (430, "不同意；不一致"),
    "do a favour": (431, "帮个忙"),
    "do away with": (432, "废除；去掉"),
    "do by": (433, "对待；对待"),
    "do down": (434, "诽谤；贬低"),
    "do for": (435, "足以；对…有用"),
    "do good": (436, "做好事；有用"),
    "do harm to": (437, "伤害；损害"),
    "do justice": (438, "公平对待；适当处理"),
    "do one's best": (439, "尽最大努力"),
    "do one's bit": (440, "尽一份力"),
    "do one's duty": (441, "尽职；尽责"),
    "do one's hair": (442, "做头发"),
    "do one's homework": (443, "做作业"),
    "do one's level best": (444, "竭尽全力"),
    "do one's utmost": (445, "尽全力"),
    "do research on": (446, "研究；调查"),
    "do sb a favour": (447, "帮某人忙"),
    "do some cleaning": (448, "打扫卫生"),
    "do sports": (449, "做运动"),
    "do the trick": (450, "奏效；达到目的"),
    "do up": (451, "修缮；整理；梳妆"),
    "do with": (452, "将就用；需要"),
    "do without": (453, "没有…也行；无需"),
    "do wrong": (454, "做错；做坏事"),
    "donate to": (455, "捐赠给"),
    "double back": (456, "折回；往回跑"),
    "down with": (457, "病倒了；染上…"),
    "dozens of": (458, "数十；许多"),
    "drag in": (459, "拉入；拖进"),
    "drag on": (460, "拖延；拖长"),
    "drain of": (461, "耗尽；流失"),
    "drain off": (462, "流走；排掉"),
    "draw a conclusion": (463, "得出结论"),
    "draw aside": (464, "拉向一边；引开"),
    "draw attention to": (465, "引起注意"),
    "draw away": (466, "拉开；引开"),
    "draw back": (467, "后退；撤退"),
    "draw in": (468, "吸引；拉进"),
    "draw into": (469, "拉入；卷入"),
    "draw lots": (470, "抽签"),
    "draw on": (471, "利用；临近"),
    "draw one's attention to": (472, "引起某人注意"),
    "draw out": (473, "拉长；取出"),
    "draw up": (474, "起草；拟定；停下"),
    "draw upon": (475, "利用；依靠"),
    "dream about": (476, "梦想；梦见"),
    "dream of": (477, "梦想；向往"),
    "dream up": (478, "虚构；设想"),
    "dress sb up": (479, "给…穿衣服"),
    "dress up": (480, "打扮；穿上盛装"),
    "drink down": (481, "吞下；喝下去"),
    "drink to": (482, "为…干杯"),
    "drink up": (483, "喝光；喝完"),
    "drive at": (484, "意在；针对"),
    "drive away": (485, "赶走；开走"),
    "drive home": (486, "把…敲进；使人理解"),
    "drive out": (487, "驱赶；凿出"),
    "drive up": (488, "抬高；开车上来"),
    "drop away": (489, "减少；离去"),
    "drop by": (490, "顺便走访"),
    "drop in": (491, "顺便走访"),
    "drop off": (492, "减少；让…下车"),
    "drop on": (493, "拜访；投弹"),
    "drop out": (494, "退出；退学；脱落"),
    "drop over": (495, "顺便来访"),
    "drop to one's knees": (496, "跪下"),
    "dry out": (497, "干涸；弄干"),
    "dry sb out": (498, "榨干某人的钱财"),
    "dry up": (499, "干涸；枯竭"),
    "due to": (500, "由于；应归于"),
    "dwell on": (501, "详述；细想"),
    "each other": (502, "彼此；互相"),
    "early or late": (503, "迟早"),
    "earn a living": (504, "谋生"),
    "earn one's living": (505, "谋生"),
    "ease off": (506, "减缓；放松"),
    "ease up": (507, "减缓；放松"),
    "eat up": (508, "吃光；耗尽"),
    "eat one's word": (509, "食言；违背诺言"),
    "either or": (510, "或…或…；不是…就是"),
    "employ oneself in": (511, "从事；忙于"),
    "empty of": (512, "缺乏；空的"),
    "end in": (513, "以…结束；结果为"),
    "end off": (514, "结束"),
    "end up": (515, "最终；结果；结束"),
    "end up as": (516, "最终成为"),
    "end up doing": (517, "最终在做"),
    "end up with": (518, "最终得到；以…结束"),
    "engaged in": (519, "从事于；忙于"),
    "enjoy oneself": (520, "过得愉快"),
    "ensure against": (521, "防备；预防"),
    "enter for": (522, "报名参加"),
    "enter into": (523, "进入；订立；讨论"),
    "enter upon": (524, "开始讨论；着手"),
    "equip with": (525, "装备；配备"),
    "escape from prison": (526, "越狱"),
    "evade duty": (527, "逃避责任"),
    "even as": (528, "正当…时候；即使"),
    "even if": (529, "即使；虽然"),
    "even now": (530, "即使在现在"),
    "even so": (531, "虽然如此；尽管这样"),
    "even though": (532, "即使；虽然"),
    "every now and again": (533, "时常；不时"),
    "every now and then": (534, "时常；不时"),
    "every other": (535, "每隔一个"),
    "every so often": (536, "时常；不时"),
    "except for": (537, "除…外；只是"),
    "exert oneself to": (538, "努力；尽力"),
    "exist in": (539, "存在于"),
    "exist on": (540, "靠…生存"),
    "expect of": (541, "期待；指望"),
    "expose to": (542, "暴露于；接触"),
    "express an interest in": (543, "表示对…感兴趣"),
    "express interest in": (544, "表示对…感兴趣"),
    "face to face": (545, "面对面"),
    "face up to": (546, "勇敢面对；承认"),
    "fade away": (547, "消退；消失"),
    "fail in": (548, "失败；不及格"),
    "fail to": (549, "未能；没有…"),
    "fall back on": (550, "求助于；转而依靠"),
    "fall behind": (551, "落后；拖欠"),
    "fall for": (552, "迷恋；受骗"),
    "fall in love": (553, "爱上"),
    "fall in love with": (554, "爱上"),
    "fall in with": (555, "偶尔遇到；同意"),
    "fall into": (556, "落入；养成；开始"),
    "fall into a decline": (557, "陷入衰退"),
    "fall into an error": (558, "犯错误"),
    "fall out": (559, "争吵；脱落；发生"),
    "fall out of": (560, "退出；不再属于"),
    "fall over": (561, "摔倒；跌倒"),
    "fall through": (562, "落空；失败"),
    "fall to": (563, "落到；沦为"),
    "fall under": (564, "归入；受到"),
    "far and away": (565, "显然；远远"),
    "far and near": (566, "到处；远近"),
    "far from": (567, "远非；完全不"),
    "far too": (568, "太…了"),
    "fear for": (569, "为…担心"),
    "feed on": (570, "以…为食；从…获取"),
    "feed up": (571, "养肥；喂饱"),
    "feed with": (572, "用…喂养"),
    "feel amused at": (573, "觉得好笑"),
    "feel an interest in": (574, "对…感兴趣"),
    "feel interested in": (575, "对…感兴趣"),
    "feel like": (576, "想要；想做"),
    "feel one's way": (577, "摸索前进"),
    "feel out": (578, "摸出来；试探"),
    "feel up to": (579, "觉得能胜任"),
    "figure on": (580, "指望；计划"),
    "figure out": (581, "想出；弄明白"),
    "fill in": (582, "填写；填充；代班"),
    "fill out": (583, "填写；使丰满"),
    "fill up": (584, "填满；装满"),
    "find expression in": (585, "在…中得到表达"),
    "find oneself": (586, "发觉自己的处境"),
    "find out": (587, "找出；查明；发现"),
    "finish up": (588, "完成；结束"),
    "finish up with": (589, "以…完成；结束"),
    "finish with": (590, "完成；结束"),
    "fire up": (591, "点火；激起；生火"),
    "first and foremost": (592, "首先；首要的是"),
    "first of all": (593, "首先；第一"),
    "first or last": (594, "总之；好歹"),
    "fish out": (595, "捞出；找出"),
    "fix attention on": (596, "注意"),
    "fix on": (597, "选定；决定"),
    "fix one's attention on": (598, "注意"),
    "fix one's eyes on": (599, "注视；盯着"),
    "fix one's mind on": (600, "专心于"),
    "fix up": (601, "安排；修理；解决"),
    "fix upon": (602, "选定；决定"),
    "flame out": (603, "熄灭；发怒"),
    "flare up": (604, "突然发怒；突然燃烧"),
    "flash out": (605, "突然显出；闪现"),
    "fly into a temper": (606, "大怒；勃然大怒"),
    "focus on": (607, "聚焦于；集中于"),
    "focus upon": (608, "聚焦于；集中于"),
    "follow one's advice": (609, "听从某人的建议"),
    "follow one's example": (610, "效法某人的榜样"),
    "follow one's lead": (611, "以某人为首；效法某人"),
    "follow sb's advice": (612, "听从某人的建议"),
    "follow sb's example": (613, "效法某人的榜样"),
    "follow sb's lead": (614, "以某人为首；效法某人"),
    "follow through": (615, "贯彻到底；坚持到底"),
    "follow up": (616, "跟进；追踪"),
    "for a start": (617, "首先；作为开始"),
    "for ages": (618, "很久；许久"),
    "for certain": (619, "肯定；无疑"),
    "for company": (620, "作伴；陪伴"),
    "for ever": (621, "永远"),
    "for example": (622, "例如"),
    "for fear of": (623, "唯恐；以免"),
    "for free": (624, "免费"),
    "for fun": (625, "为了好玩；闹着玩"),
    "for good": (626, "永久地；一劳永逸"),
    "for lack of": (627, "因缺乏"),
    "for life": (628, "终身；一生"),
    "for long": (629, "长久"),
    "for nothing": (630, "免费；白白"),
    "for one's part": (631, "就某人而言"),
    "for sale": (632, "待售；出售的"),
    "for short": (633, "简称；缩写"),
    "for sure": (634, "肯定；无疑"),
    "for the benefit of": (635, "为了…的利益"),
    "for the best": (636, "为了最好；出于好意"),
    "for the better": (637, "为了更好；好转"),
    "for the future": (638, "为了将来"),
    "for the meantime": (639, "暂时；在此期间"),
    "for the moment": (640, "暂时；此刻"),
    "for the time being": (641, "暂时；眼下"),
    "forget about": (642, "忘记；忽略"),
    "free and easy": (643, "自由自在；无拘束"),
    "free from": (644, "免于；不受…影响"),
    "free of": (645, "免于；摆脱"),
    "free of charge": (646, "免费"),
    "freeze up": (647, "冻结；僵住"),
    "from day to day": (648, "天天；逐日"),
    "from rags to riches": (649, "白手起家；从贫到富"),
    "from the beginning": (650, "从一开始"),
    "from the bottom": (651, "从底层；从零开始"),
    "from the bottom of one's heart": (652, "发自内心深处"),
    "from time to time": (653, "有时；不时"),
    "gain a seat": (654, "获得席位"),
    "gain control of": (655, "取得控制权"),
    "gain on": (656, "胜过；逼近"),
    "gain weight": (657, "体重增加"),
    "gaze at": (658, "凝视；盯着看"),
    "generation gap": (659, "代沟"),
    "get about": (660, "走动；传播"),
    "get above oneself": (661, "自命不凡"),
    "get across": (662, "被理解；通过"),
    "get ahead": (663, "进步；成功"),
    "get along": (664, "相处；进展"),
    "get along with": (665, "与…相处；进展"),
    "get around": (666, "规避；四处走动"),
    "get at": (667, "触及；意思是"),
    "get away": (668, "离开；逃脱"),
    "get away from": (669, "逃离；摆脱"),
    "get away with": (670, "侥幸成功；逃脱惩罚"),
    "get back at": (671, "报复"),
    "get by": (672, "过活；通过"),
    "get control of": (673, "控制"),
    "get credit for": (674, "因…而受到称赞"),
    "get down": (675, "写下；使沮丧"),
    "get down to": (676, "开始认真处理"),
    "get hold of": (677, "抓住；找到"),
    "get in": (678, "进入；收获；当选"),
    "get in touch": (679, "取得联系"),
    "get in touch with": (680, "与…取得联系"),
    "get into": (681, "进入；陷入；习惯于"),
    "get into debt": (682, "负债"),
    "get into trouble": (683, "惹上麻烦"),
    "get involved in": (684, "参与；卷入；涉及"),
    "get lost": (685, "迷路；迷失"),
    "get off": (686, "下车；脱身；下班"),
    "get on": (687, "上车；进展；相处"),
    "get on to": (688, "转入；谈起新话题"),
    "get on well with": (689, "与…相处融洽"),
    "get on with": (690, "继续；相处；上车"),
    "get one's breath back": (691, "喘口气；歇一歇"),
    "get one's hands on": (692, "找到；获得"),
    "get out": (693, "出去；泄露；逃脱"),
    "get out of": (694, "走出；摆脱；从…出来"),
    "get out of control": (695, "失控"),
    "get over": (696, "克服；恢复；熬过"),
    "get rid of": (697, "摆脱；除去"),
    "get sight of": (698, "看见；发现"),
    "get stuck": (699, "卡住；被困"),
    "get the best of": (700, "占…便宜；胜过"),
    "get the better of": (701, "占…便宜；胜过"),
    "get the phone": (702, "接电话"),
    "get through": (703, "完成；接通；度过"),
    "get tired of": (704, "厌倦；厌烦"),
    "get to the point": (705, "说到要点"),
    "get together": (706, "聚会；聚集"),
    "get up": (707, "起床；站起来；增加"),
    "give a lead": (708, "带头；树立榜样"),
    "give a look": (709, "看一看"),
    "give a speech": (710, "发表演讲"),
    "give a warning": (711, "发出警告"),
    "give ear to": (712, "倾听；注意"),
    "give expression to": (713, "表达；表现"),
    "give in": (714, "屈服；让步；交上"),
    "give off": (715, "发出；放出"),
    "give one's ears": (716, "倾听；注意"),
    "give out": (717, "分发；公布；用尽"),
    "give preference to": (718, "优先考虑；偏爱"),
    "give rise to": (719, "引起；导致"),
    "give rise to sth": (720, "引起；导致"),
    "give sb a lead": (721, "带头；树立榜样"),
    "give sb a lift": (722, "让…搭车"),
    "give sb a look": (723, "让…看一看"),
    "give up": (724, "放弃；投降；交出"),
    "give way to": (725, "让路；让位于"),
    "glance at": (726, "瞥一眼；扫视"),
    "glance through": (727, "浏览；粗略看"),
    "glare at": (728, "怒目而视；瞪着眼看"),
    "go about": (729, "着手；四处走动"),
    "go after": (730, "追求；追逐"),
    "go against": (731, "反对；不利于"),
    "go ahead": (732, "前进；开始；先走"),
    "go all out": (733, "全力以赴"),
    "go along": (734, "前进；赞同；同行"),
    "go around": (735, "四处走动；流传"),
    "go back on": (736, "违背；食言"),
    "go back to": (737, "回到；回顾"),
    "go beyond": (738, "超出；越过"),
    "go by": (739, "经过；过去；依照"),
    "go crazy": (740, "发疯；发狂"),
    "go down": (741, "下沉；下降；被记下"),
    "go for": (742, "争取；追求；袭击"),
    "go hard": (743, "努力；苛刻"),
    "go hard with": (744, "对…苛刻；严厉"),
    "go in for": (745, "从事；爱好；主张"),
    "go into": (746, "进入；讨论；详述"),
    "go into action": (747, "行动起来"),
    "go into battle": (748, "参战；战斗"),
    "go into detail": (749, "详细说明"),
    "go into details": (750, "详细说明"),
    "go off": (751, "离开；爆炸；变质"),
    "go off with": (752, "与…私奔；带走"),
    "go on": (753, "继续；发生；上演"),
    "go on a diet": (754, "节食；减肥"),
    "go on show": (755, "展出；表演"),
    "go out": (756, "出去；熄灭；过时"),
    "go out of one's way": (757, "特意；不怕麻烦"),
    "go over": (758, "复习；检查；重温"),
    "go through": (759, "经历；仔细检查；用完"),
    "go to excess": (760, "过度；走得过远"),
    "go to great lengths": (761, "竭尽全力；不惜一切"),
    "go to the expense of": (762, "不惜费用；花钱"),
    "go to work": (763, "去上班；开始工作"),
    "go together": (764, "相配；协调；交往"),
    "go up": (765, "上升；上涨；建起"),
    "go with": (766, "伴随；搭配；同意"),
    "go without": (767, "没有…也行；无需"),
    "good deed": (768, "好事；善行"),
    "good for": (769, "对…有益；有效"),
    "grasp at": (770, "试图抓住；急于接受"),
    "grow on": (771, "越来越喜欢；加深印象"),
    "grow up": (772, "长大；成长；发展"),
    "guarantee against": (773, "保证…不；防止"),
    "had best": (774, "最好；还是…好"),
    "had better": (775, "最好；还是…好"),
    "hand back": (776, "交还；归还"),
    "hand down": (777, "传下来；宣布"),
    "hand in": (778, "交上；递交"),
    "hand in hand": (779, "手拉手；密切关联"),
    "hand on": (780, "转交；传下来"),
    "hand out": (781, "分发；施舍"),
    "hand over": (782, "移交；交出"),
    "hang about": (783, "闲逛；徘徊"),
    "hang around": (784, "闲逛；徘徊"),
    "hang in": (785, "坚持；不挂断"),
    "hang on": (786, "等待；紧抓不放；不挂断"),
    "hang on to": (787, "紧紧抓住；保留"),
    "hang out with": (788, "与…混在一起；经常来往"),
    "hang up": (789, "挂断电话；搁置；挂起"),
    "happen on": (790, "偶然发生"),
    "happen to": (791, "碰巧；恰好"),
    "hardly any": (792, "几乎没有；很少"),
    "hardly when": (793, "几乎不在…时候"),
    "have a ball": (794, "玩得痛快；过得愉快"),
    "have a class": (795, "上课"),
    "have a cold": (796, "感冒"),
    "have a desire to do": (797, "想要做"),
    "have a dislike of": (798, "不喜欢；厌恶"),
    "have a fever": (799, "发烧"),
    "have a gift for": (800, "有…的天赋"),
    "have a go": (801, "试一试"),
    "have a good time": (802, "玩得愉快；过得愉快"),
    "have a great time": (803, "玩得愉快；过得愉快"),
    "have a hand in": (804, "参与；插手；有一份功劳"),
    "have a look at": (805, "看一看"),
    "have a say in": (806, "有发言权；参与意见"),
    "have a talent for": (807, "有…的天赋"),
    "have a taste for": (808, "对…有兴趣；爱好"),
    "have a taste of": (809, "尝一尝；体验一下"),
    "have a try": (810, "试一试"),
    "have a walk": (811, "散步"),
    "have a word with": (812, "和…谈谈；和…说句话"),
    "have an advantage": (813, "有优势；有利条件"),
    "have an appetite for": (814, "想吃；渴望"),
    "have an effect on": (815, "对…有影响"),
    "have an eye for": (816, "有鉴赏力；有眼光"),
    "have an eye to": (817, "留意；照看"),
    "have an impact on": (818, "对…有影响"),
    "have an influence on": (819, "对…有影响"),
    "have back": (820, "收回；拿回"),
    "have classes": (821, "上课"),
    "have common interests": (822, "有共同利益；有共同兴趣"),
    "have difficulty in": (823, "在…方面有困难"),
    "have egg on one's face": (824, "丢脸；出丑"),
    "have faith in": (825, "信仰；信任"),
    "have fun": (826, "玩得开心；过得愉快"),
    "have fun in": (827, "在…中玩得开心"),
    "have fun with": (828, "和…一起玩得开心"),
    "have got to": (829, "必须；不得不"),
    "have in common": (830, "有共同之处；相同"),
    "have in common with": (831, "和…有共同之处"),
    "have influence on": (833, "对…有影响"),
    "have no business": (834, "无权；不该"),
    "have no faith in": (835, "不信任；不相信"),
    "have no lack of": (836, "不缺；充足"),
    "have no say in": (837, "无发言权；无权过问"),
    "have on": (838, "穿着；有…在手头"),
    "have one's day": (839, "得意；走运"),
    "have one's say": (840, "表达意见；发言"),
    "have possession of": (841, "占有；拥有"),
    "have sight of": (842, "看见；发现"),
    "have something to do with": (843, "和…有关；与…有关系"),
    "have sth in stock": (844, "有…存货；存有"),
    "have sth on one's mind": (845, "惦记；想着"),
    "have sth to do": (846, "有事要做；有任务"),
    "have sth to do with": (847, "和…有关；与…有关系"),
    "have to": (848, "必须；不得不"),
    "have to do": (849, "必须做；不得不做"),
    "have to do with": (850, "和…有关；与…有关系"),
    "have trouble doing": (851, "做…有困难"),
    "have trouble doing sth": (852, "做…有困难"),
    "have trouble in doing": (853, "在…方面有困难"),
    "have trouble in doing sth": (854, "在…方面有困难"),
    "have trouble with": (855, "有困难；有问题"),
    "have words with": (856, "和…吵架；争论"),
    "head for": (857, "朝…出发；前往"),
    "head on": (858, "迎面冲突；继续前进"),
    "head up": (859, "率领；带领"),
    "hear about": (860, "听说；得知"),
    "hear from": (861, "收到…的信/电话"),
    "hear of": (862, "听说；知道"),
    "hear out": (863, "听完；听到底"),
    "heart and soul": (864, "全心全意地"),
    "heart to heart": (865, "推心置腹地；诚恳地"),
    "help oneself": (866, "自取；自用"),
    "help oneself to": (867, "自取；随便吃"),
    "help out": (868, "帮助…解决问题"),
    "help sb out": (869, "帮助某人"),
    "help sb with sth": (870, "在某事上帮助某人"),
    "help with": (871, "帮助；帮忙"),
    "here and now": (872, "此时此地；立刻"),
    "here and there": (873, "各处；零星散布"),
    "here you are": (874, "给你；这就是你要的"),
    "hit on": (875, "偶然想到；忽然想到"),
    "hit upon": (876, "偶然想到；忽然想到"),
    "hold against": (877, "因…而怀恨在心"),
    "hold back": (878, "阻止；隐瞒；犹豫"),
    "hold breath": (879, "屏住呼吸"),
    "hold down": (880, "压制；压低；保持"),
    "hold in": (881, "约束；抑制；容纳"),
    "hold in arms": (882, "拥抱；抱住"),
    "hold office": (883, "任职；执政"),
    "hold on": (884, "等一下；抓紧；坚持"),
    "hold on to": (885, "紧紧抓住；不放"),
    "hold one's breath": (886, "屏住呼吸"),
    "hold one's own": (887, "坚持己见；自主"),
    "hold oneself in": (888, "克制；自制"),
    "hold out": (889, "伸出；坚持；维持"),
    "hold sb in one's arms": (890, "拥抱某人"),
    "hold up": (891, "支撑；阻挡；抢劫"),
}


def load_source_b() -> dict[str, dict]:
    """Parse the 236 high-frequency phrase PDF content.

    Returns {normalized_phrase: {"rank": int, "definitions": [str]}}.
    """
    print("[Source B] Loading 236 high-frequency phrases ...")
    result: dict[str, dict] = {}
    for key, (rank, definition) in _PDF_ENTRIES.items():
        norm_key = normalize_phrase(key)
        if norm_key:
            result[norm_key] = {"rank": rank, "definitions": [definition]}
    print(f"[Source B] Loaded {len(result)} entries")
    return result


# ---------------------------------------------------------------------------
# Source C: maimemo-export CSV
# ---------------------------------------------------------------------------


def load_source_c() -> dict[str, list[str]]:
    """Download and parse maimemo-export CSV.

    Returns {normalized_phrase: [definition_strings]}.
    """
    print(f"[Source C] Downloading {SOURCE_C_CSV_URL} ...")
    result: dict[str, list[str]] = {}
    try:
        resp = urlopen(SOURCE_C_CSV_URL, timeout=30)
        raw = resp.read().decode("utf-8-sig", errors="replace")
    except (URLError, OSError) as e:
        print(f"[Source C] WARNING: download failed ({e})")
        return result

    lines = raw.splitlines()
    if len(lines) < 2:
        print("[Source C] ERROR: empty CSV")
        return result

    header = lines[0]
    # Detect column indices
    parts = header.split(",")
    phrase_col = 0
    def_col = 1
    if len(parts) >= 2:
        for i, p in enumerate(parts):
            low = p.strip().lower()
            if "phrase" in low or "english" in low or "词组" in low:
                phrase_col = i
            elif "chinese" in low or "meaning" in low or "释义" in low or "翻译" in low:
                def_col = i

    for line in lines[1:]:
        cols = line.split(",")
        if len(cols) > max(phrase_col, def_col):
            phrase = cols[phrase_col].strip()
            defn = cols[def_col].strip()
            if phrase and defn:
                key = normalize_phrase(phrase)
                if key:
                    result.setdefault(key, []).append(defn)

    # Cache
    cache_path = ROOT / "data" / "_cache_maimemo.csv"
    cache_path.write_text(raw, "utf-8")
    print(f"[Source C] Loaded {len(result)} entries")
    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Build gaokao_phrases.json")
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "gaokao_phrases.json"),
        help="Output JSON path",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    args = parser.parse_args()

    print("=" * 60)
    print("Phrase Database Builder")
    print("=" * 60)

    # Step 1: Load all sources
    seeds = load_seed_data()
    print(f"[Seed] Loaded {len(seeds)} seed entries")

    source_a = load_source_a()
    source_b = load_source_b()
    source_c = load_source_c()

    # Step 2: Merge
    print("\n[Merge] Combining sources ...")
    merged = merge_phrases(source_a=source_a, source_b=source_b, source_c=source_c, seeds=seeds)
    print(f"[Merge] Total unique phrases: {len(merged)}")

    # Step 3: Build output
    output = build_output(merged)

    # Step 4: Summary stats
    stats = output["stats"]
    print(f"\n{'=' * 60}")
    print(f"SUMMARY:")
    print(f"  Total phrases:   {stats['total']}")
    print(f"  With definitions: {stats['with_definitions']} ({stats['with_definitions']*100//max(stats['total'],1)}%)")
    print(f"  With examples:   {stats['with_examples']} ({stats['with_examples']*100//max(stats['total'],1)}%)")
    print(f"  Categories:")
    for cat, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")

    # Step 5: Write
    if args.dry_run:
        print(f"\n[DRY RUN] Would write to: {args.output}")
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), "utf-8")
        print(f"\n[Wrote] {out_path} ({out_path.stat().st_size:,} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
