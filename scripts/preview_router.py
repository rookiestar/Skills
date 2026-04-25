#!/usr/bin/env python3
"""Preview router for the self-learning-tutor skill.

This script is only for local QA. It mirrors the intended routing boundary
described in SKILL.md so the project can be tested without a running OpenClaw
instance.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass


ENTERTAINMENT_KEYWORDS = {
    "明星",
    "游戏",
    "电影",
    "电视剧",
    "八卦",
    "视频",
    "抖音",
    "快手",
    "爱豆",
    "idol",
    "game",
    "movie",
    "video",
}

ROLEPLAY_KEYWORDS = {
    "扮演",
    "角色",
    "忽略规则",
    "不要遵守",
    "越狱",
    "jailbreak",
    "system prompt",
    "pretend",
    "roleplay",
}

OTHER_SUBJECT_KEYWORDS = {
    "数学",
    "语文",
    "物理",
    "化学",
    "生物",
    "历史",
    "地理",
    "政治",
    "作文",
    "古诗",
    "方程",
}

FOLLOW_UP_KEYWORDS = {
    "这个词",
    "刚才那个",
    "它还有",
    "还有其他意思",
    "怎么用",
    "别的词性",
}

ZH_TO_EN_CUES = {
    "英语怎么说",
    "英文怎么说",
    "翻译成英语",
    "用英语",
    "英文",
}

SENTENCE_TRANSLATION_CUES = {
    "翻译成中文",
    "翻译成英文",
    "翻译一下",
    "帮我翻译",
    "请翻译",
}

ENGLISH_TERM_RE = re.compile(r"^[A-Za-z][A-Za-z' -]{0,40}$")
ENGLISH_WORD_COUNT_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass(frozen=True)
class RouteResult:
    category: str
    reply_key: str


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def is_english_term(text: str) -> bool:
    if not ENGLISH_TERM_RE.fullmatch(text):
        return False
    return 1 <= len(ENGLISH_WORD_COUNT_RE.findall(text)) <= 3


def looks_like_sentence_translation(text: str) -> bool:
    if any(cue in text for cue in SENTENCE_TRANSLATION_CUES):
        english_words = ENGLISH_WORD_COUNT_RE.findall(text)
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        if len(english_words) >= 4 or chinese_chars >= 8:
            return True
    english_words = ENGLISH_WORD_COUNT_RE.findall(text)
    return len(english_words) >= 5 and any(p in text for p in ".!?。！？")


def classify_input(text: str, last_term: str | None = None) -> RouteResult:
    text = normalize(text)
    lowered = text.lower()

    if not text:
        return RouteResult("ambiguous", "clarify_subject")

    if any(keyword in lowered for keyword in ROLEPLAY_KEYWORDS):
        return RouteResult("boundary_break", "refuse_boundary_break")

    if any(keyword in text for keyword in FOLLOW_UP_KEYWORDS):
        if last_term:
            return RouteResult("english_follow_up", "follow_up")
        return RouteResult("ambiguous", "clarify_previous_term")

    if any(keyword in text for keyword in OTHER_SUBJECT_KEYWORDS):
        return RouteResult("unsupported_subject", "unsupported_subject")

    if any(keyword in text for keyword in ENTERTAINMENT_KEYWORDS):
        return RouteResult("off_topic_chat", "refuse_off_topic")

    if looks_like_sentence_translation(text):
        return RouteResult("sentence_translation", "refuse_sentence_translation")

    if is_english_term(text) or re.search(r"[A-Za-z]", text) and "什么意思" in text:
        return RouteResult("english_lookup_en_to_zh", "english_card_en_to_zh")

    if any(cue in text for cue in ZH_TO_EN_CUES):
        return RouteResult("english_lookup_zh_to_en", "english_card_zh_to_en")

    return RouteResult("ambiguous", "clarify_subject")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview local routing for the skill")
    parser.add_argument("text", help="User input to classify")
    parser.add_argument("--last-term", default=None, help="Last queried term in session")
    args = parser.parse_args()

    result = classify_input(args.text, args.last_term)
    print(
        json.dumps(
            {"category": result.category, "reply_key": result.reply_key},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
