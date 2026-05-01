from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lookup_router import classify_input  # noqa: E402


def test_english_lookup_builds_deterministic_query() -> None:
    result = classify_input("in the future")
    assert result.category == "english_lookup_en_to_zh"
    assert result.reply_key == "english_card_en_to_zh"
    assert result.lookup_query == "in the future"


def test_single_word_lookup_routes_to_query() -> None:
    result = classify_input("quiet")
    assert result.category == "english_lookup_en_to_zh"
    assert result.lookup_query == "quiet"


def test_chinese_cue_routes_to_zh_to_en_lookup() -> None:
    result = classify_input("重要的英语怎么说")
    assert result.category == "english_lookup_zh_to_en"
    assert result.lookup_query == "重要的"


def test_off_topic_chat_is_rejected_without_model() -> None:
    result = classify_input("我想看电影")
    assert result.category == "off_topic_chat"
    assert result.reply_text == "这个我帮不上忙，有单词想查的话随时告诉我呀 📖"


def test_vague_follow_up_is_clarified_without_guessing() -> None:
    result = classify_input("这个词是什么意思")
    assert result.category == "ambiguous"
    assert result.reply_text == "你刚才查的是哪个词呀？再发我一次，我接着说 😊"


def test_question_like_english_chat_is_not_treated_as_lookup() -> None:
    result = classify_input("what is up")
    assert result.category == "ambiguous"
    assert result.reply_text == "你是要查英语单词，还是语文的内容呀？"


def test_sentence_translation_is_rejected() -> None:
    result = classify_input("Please translate this sentence for me.")
    assert result.category == "sentence_translation"
    assert result.reply_text == "句子翻译我现在还不会哦，你把里面不懂的单词或词组发给我，我来帮你查 😊"
