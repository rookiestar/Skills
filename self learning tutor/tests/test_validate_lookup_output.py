import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_lookup_output import validate


class ValidateLookupOutputTests(unittest.TestCase):
    def test_valid_en_to_zh_card(self) -> None:
        card = """**hallucination**
- 📖 词性：n.
- 🔤 音标：/həˌluːsɪˈneɪʃən/
- 🇨🇳 释义：幻觉
- 🇨🇳 释义 2：妄想
- 💬 例句：He suffered from hallucinations.（他出现了幻觉。）"""
        result = validate(card, "en_to_zh")
        self.assertTrue(result.ok, result.errors)

    def test_rejects_extra_explanation(self) -> None:
        card = """**hallucination**
- 📖 词性：n.
- 🔤 音标：/həˌluːsɪˈneɪʃən/
- 🇨🇳 释义：幻觉
- 💬 例句：He suffered from hallucinations.（他出现了幻觉。）
🔍 在AI里也常这样用"""
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("extra line" in error or "forbidden" in error for error in result.errors))

    def test_valid_zh_to_en_card(self) -> None:
        card = """**重要的**
- 🔤 最常用英文：important /ɪmˈpɔːrtnt/
- 📖 词性：adj.
- 🔤 音标：/ɪmˈpɔːrtnt/
- 🇨🇳 对应义：重要的
- 💬 例句：It is important to finish your homework on time.（按时完成作业很重要。）"""
        result = validate(card, "zh_to_en")
        self.assertTrue(result.ok, result.errors)

    def test_rejects_forbidden_snippet(self) -> None:
        card = """**important**
- 📖 词性：adj.
- 🔤 音标：/ɪmˈpɔːrtnt/
- 🇨🇳 释义：重要的
- 💬 例句：It is important to finish your homework on time.（按时完成作业很重要。）
- 词根记忆：im + port"""
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("词根" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
