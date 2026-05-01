"""Deterministic routing helpers for the self-learning-tutor skill."""

from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.dictionary_utils import normalize_query, strip_lookup_cues_en, strip_lookup_cues_zh


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
    "翻译成英文",
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

ENGLISH_TERM_RE = re.compile(r"^[A-Za-z][A-Za-z' -]{0,60}$")
ENGLISH_WORD_COUNT_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
QUESTION_WORDS = {
    "what",
    "why",
    "how",
    "who",
    "whom",
    "whose",
    "where",
    "when",
    "which",
    "can",
    "could",
    "would",
    "should",
    "is",
    "are",
    "am",
    "do",
    "does",
    "did",
    "please",
    "this",
    "that",
    "it",
    "i",
    "we",
    "you",
    "they",
    "he",
    "she",
    "there",
    "here",
}

@dataclass(frozen=True)
class RouteResult:
    category: str
    reply_key: str
    lookup_query: str | None = None
    reply_text: str | None = None


def normalize(text: str) -> str:
    return normalize_query(text)


def is_english_term(text: str) -> bool:
    if not ENGLISH_TERM_RE.fullmatch(text):
        return False
    words = ENGLISH_WORD_COUNT_RE.findall(text)
    return 1 <= len(words) <= 5


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
        return RouteResult("ambiguous", "clarify_subject", reply_text="你是要查英语单词，还是语文的内容呀？")

    if any(keyword in lowered for keyword in ROLEPLAY_KEYWORDS):
        return RouteResult("boundary_break", "refuse_boundary_break", reply_text="我只是小问，专心帮你学习的那种～有题目吗？")

    if any(keyword in text for keyword in FOLLOW_UP_KEYWORDS):
        if last_term:
            return RouteResult("english_follow_up", "follow_up", reply_text="有的，我可以继续补第 3 个，如果 Cambridge 里明确有的话。")
        return RouteResult("ambiguous", "clarify_previous_term", reply_text="你刚才查的是哪个词呀？再发我一次，我接着说 😊")

    if any(keyword in text for keyword in OTHER_SUBJECT_KEYWORDS):
        return RouteResult("unsupported_subject", "unsupported_subject", reply_text="这个科目我还在学习中，很快就能帮你啦 📚")

    if any(keyword in text for keyword in ENTERTAINMENT_KEYWORDS):
        return RouteResult("off_topic_chat", "refuse_off_topic", reply_text="这个我帮不上忙，有单词想查的话随时告诉我呀 📖")

    if looks_like_sentence_translation(text):
        return RouteResult(
            "sentence_translation",
            "refuse_sentence_translation",
            reply_text="句子翻译我现在还不会哦，你把里面不懂的单词或词组发给我，我来帮你查 😊",
        )

    english_words = ENGLISH_WORD_COUNT_RE.findall(text)
    if len(english_words) > 1 and english_words[0].lower() in QUESTION_WORDS:
        return RouteResult("ambiguous", "clarify_subject", reply_text="你是要查英语单词，还是语文的内容呀？")

    stripped_en = strip_lookup_cues_en(text)
    if stripped_en != text and is_english_term(stripped_en):
        return RouteResult("english_lookup_en_to_zh", "english_card_en_to_zh", lookup_query=normalize(stripped_en))

    stripped_zh = strip_lookup_cues_zh(text)
    if stripped_zh != text and stripped_zh:
        return RouteResult("english_lookup_zh_to_en", "english_card_zh_to_en", lookup_query=normalize(stripped_zh))

    if is_english_term(text):
        return RouteResult("english_lookup_en_to_zh", "english_card_en_to_zh", lookup_query=normalize(text))

    if any(cue in text for cue in ZH_TO_EN_CUES):
        cleaned = strip_lookup_cues_zh(text)
        if cleaned:
            return RouteResult("english_lookup_zh_to_en", "english_card_zh_to_en", lookup_query=normalize(cleaned))

    return RouteResult("ambiguous", "clarify_subject", reply_text="你是要查英语单词，还是语文的内容呀？")
