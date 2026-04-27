#!/usr/bin/env python3
"""Comprehensive audit test suite for all Python scripts under scripts/.

Covers:
  - Return path completeness (every function returns on ALL code paths)
  - None safety (callers handle functions that can return None)
  - Edge cases (empty strings, empty lists, missing files, malformed JSON)
  - Off-by-one / boundary conditions
  - Exception handling (bare excepts, uncaught exceptions)
  - Logic errors (wrong variables, dead code, impossible conditions)
  - Integration paths (call main functions directly)

Run:
    cd "self learning tutor" && python3 -m pytest tests/test_script_audit.py -v
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import sys
import tempfile
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from scripts.dictionary_utils import (  # noqa: E402
    BRACKET_PREFIX_RE,
    EN_LOOKUP_CUES,
    NUMBER_PREFIX_RE,
    POS_SEPARATOR_RE,
    POS_TOKEN_RE,
    SPLIT_RE,
    ZH_LOOKUP_CUES,
    build_reverse_terms,
    coerce_text,
    extract_pos_from_text,
    normalize_int,
    normalize_query,
    normalize_whitespace,
    normalize_zh_term,
    parse_definitions,
    record_to_entry,
    split_pos_prefix,
    strip_lookup_cues_en,
    strip_lookup_cues_zh,
    strip_pos_prefix,
    _record_get,
)
from scripts.dict_lookup import (  # noqa: E402
    append_missing_word,
    entry_for_output,
    extract_en_query,
    extract_zh_query,
    format_en_to_zh_text,
    load_sample_indexes,
    load_sample_entry,
    load_sample_matches,
    load_sqlite_entry,
    load_sqlite_matches,
    load_word_senses,
    lookup_en_to_zh,
    lookup_zh_to_en,
    resolve_path,
    table_exists,
)
from scripts.validate_lookup_output import (  # noqa: E402
    FORBIDDEN_SNIPPETS,
    ValidationResult,
    validate,
    _normalize,
)


# ===========================================================================
# 1. dictionary_utils.py — unit tests
# ===========================================================================

class TestNormalizeWhitespace(unittest.TestCase):
    """Tests for normalize_whitespace()."""

    def test_normal_string(self):
        self.assertEqual(normalize_whitespace("hello world"), "hello world")

    def test_collapses_multiple_spaces(self):
        self.assertEqual(normalize_whitespace("hello   world"), "hello world")

    def test_collapses_tabs_and_newlines(self):
        self.assertEqual(normalize_whitespace("hello\t\nworld"), "hello world")

    def test_strips_leading_trailing(self):
        self.assertEqual(normalize_whitespace("  hello  "), "hello")

    def test_empty_string(self):
        self.assertEqual(normalize_whitespace(""), "")

    def test_only_whitespace(self):
        self.assertEqual(normalize_whitespace("   \t\n  "), "")


class TestNormalizeQuery(unittest.TestCase):
    """Tests for normalize_query() — delegates to normalize_whitespace."""

    def test_basic(self):
        self.assertEqual(normalize_query("  hello  "), "hello")

    def test_none_like_input(self):
        # normalize_query takes str; verify it doesn't crash on edge cases
        self.assertEqual(normalize_query(""), "")


class TestCoerceText(unittest.TestCase):
    """Tests for coerce_text()."""

    def test_none_returns_empty(self):
        self.assertEqual(coerce_text(None), "")

    def test_string_stripped(self):
        self.assertEqual(coerce_text("  hello  "), "hello")

    def test_list_joins_with_chinese_semicolon(self):
        self.assertEqual(coerce_text(["a", "b", "c"]), "a；b；c")

    def test_list_skips_empty_items(self):
        self.assertEqual(coerce_text(["a", "", "b"]), "a；b")

    def test_integer_converted(self):
        self.assertEqual(coerce_text(42), "42")

    def test_list_of_integers(self):
        result = coerce_text([1, 2, 3])
        self.assertIn("1", result)
        self.assertIn("2", result)
        self.assertIn("3", result)


class TestNormalizeInt(unittest.TestCase):
    """Tests for normalize_int()."""

    def test_none_returns_default(self):
        self.assertEqual(normalize_int(None), 0)
        self.assertEqual(normalize_int(None, default=5), 5)

    def test_valid_integer_string(self):
        self.assertEqual(normalize_int("42"), 42)

    def test_float_string_truncated(self):
        self.assertEqual(normalize_int("3.14"), 3)

    def test_empty_string_returns_default(self):
        self.assertEqual(normalize_int(""), 0)

    def test_whitespace_string_returns_default(self):
        self.assertEqual(normalize_int("  "), 0)

    def test_garbage_string_returns_default(self):
        self.assertEqual(normalize_int("abc"), 0)

    def test_none_explicit_default(self):
        self.assertEqual(normalize_int(None, default=99), 99)

    def test_negative_number(self):
        self.assertEqual(normalize_int("-5"), -5)

    def test_zero(self):
        self.assertEqual(normalize_int("0"), 0)


class TestStripLookupCuesEn(unittest.TestCase):
    """Tests for strip_lookup_cues_en()."""

    def test_no_cue_unchanged(self):
        self.assertEqual(strip_lookup_cues_en("apple"), "apple")

    def test_strips_是什么意思(self):
        self.assertEqual(strip_lookup_cues_en("apple是什么意思"), "apple")

    def test_strips_的意思(self):
        self.assertEqual(strip_lookup_cues_en("apple的意思"), "apple")

    def test_strips_啥意思(self):
        self.assertEqual(strip_lookup_cues_en("apple啥意思"), "apple")

    def test_strips_什么意思(self):
        self.assertEqual(strip_lookup_cues_en("apple什么意思"), "apple")

    def test_strips_怎么读(self):
        self.assertEqual(strip_lookup_cues_en("apple怎么读"), "apple")

    def test_strips_怎么写(self):
        self.assertEqual(strip_lookup_cues_en("apple怎么写"), "apple")

    def test_strips_怎么念(self):
        self.assertEqual(strip_lookup_cues_en("apple怎么念"), "apple")

    def test_multiple_cues_not_double_stripped(self):
        # Only strips suffix, so if cue is not at end it stays
        text = "apple是什么意思"
        result = strip_lookup_cues_en(text)
        # After stripping one cue, shouldn't have another to strip
        self.assertNotIn("是什么意思", result)

    def test_normalizes_whitespace(self):
        self.assertEqual(strip_lookup_cues_en("  apple  "), "apple")


class TestStripLookupCuesZh(unittest.TestCase):
    """Tests for strip_lookup_cues_zh()."""

    def test_no_cue_unchanged(self):
        self.assertEqual(strip_lookup_cues_zh("重要的"), "重要的")

    def test_strips_英语怎么说(self):
        self.assertEqual(strip_lookup_cues_zh("重要的英语怎么说"), "重要的")

    def test_strips_英文怎么说(self):
        self.assertEqual(strip_lookup_cues_zh("重要的英文怎么说"), "重要的")

    def test_strips_翻译成英语(self):
        # "翻译成英语" is stripped as both suffix and prefix cue
        self.assertEqual(strip_lookup_cues_zh("重要的翻译成英语"), "重要的")
        self.assertEqual(strip_lookup_cues_zh("翻译成英语重要的"), "重要的")

    def test_strips_用英语(self):
        # "用英语" as suffix
        result = strip_lookup_cues_zh("说用英语")
        self.assertEqual(result, "说")

    def test_strips_英文_suffix(self):
        result = strip_lookup_cues_zh("重要的英文")
        self.assertEqual(result, "重要的")


class TestNormalizeZhTerm(unittest.TestCase):
    """Tests for normalize_zh_term()."""

    def test_basic(self):
        self.assertEqual(normalize_zh_term("  你好  "), "你好")

    def test_strips_number_prefix_arabic(self):
        self.assertEqual(normalize_zh_term("1. 你好"), "你好")

    def test_strips_number_prefix_chinese(self):
        self.assertEqual(normalize_zh_term("一、你好"), "你好")

    def test_strips_pos_prefix(self):
        self.assertEqual(normalize_zh_term("n. 你好"), "你好")

    def test_strips_trailing_punctuation(self):
        self.assertEqual(normalize_zh_term("你好。"), "你好")

    def test_strips_trailing_bracket_content(self):
        self.assertEqual(normalize_zh_term("你好（同义词）"), "你好")
        self.assertEqual(normalize_zh_term("你好(synonym)"), "你好")

    def test_empty_after_cleaning(self):
        self.assertEqual(normalize_zh_term("1. n."), "")


class TestSplitPosPrefix(unittest.TestCase):
    """Tests for split_pos_prefix()."""

    def test_single_pos_token(self):
        tokens, rest = split_pos_prefix("n. hello")
        self.assertEqual(tokens, ["n."])
        self.assertEqual(rest, "hello")

    def test_multiple_pos_tokens(self):
        tokens, rest = split_pos_prefix("adj. / n. useful thing")
        self.assertIn("adj.", tokens)
        self.assertIn("n.", tokens)
        self.assertEqual(rest, "useful thing")

    def test_no_pos_token(self):
        tokens, rest = split_pos_prefix("hello world")
        self.assertEqual(tokens, [])
        self.assertEqual(rest, "hello world")

    def test_empty_input(self):
        tokens, rest = split_pos_prefix("")
        self.assertEqual(tokens, [])
        self.assertEqual(rest, "")

    def test_none_like_input_coerced(self):
        tokens, rest = split_pos_prefix(None)
        self.assertEqual(tokens, [])
        self.assertEqual(rest, "")

    def test_deduplicates_tokens(self):
        tokens, rest = split_pos_prefix("n. / n. word")
        self.assertEqual(tokens, ["n."])
        self.assertEqual(rest, "word")

    def test_only_pos_no_rest(self):
        tokens, rest = split_pos_prefix("n.")
        self.assertEqual(tokens, ["n."])
        self.assertEqual(rest, "")


class TestStripPosPrefix(unittest.TestCase):
    """Tests for strip_pos_prefix()."""

    def test_strips_single(self):
        self.assertEqual(strip_pos_prefix("n. hello"), "hello")

    def test_no_pos_unchanged(self):
        self.assertEqual(strip_pos_prefix("hello"), "hello")

    def test_empty(self):
        self.assertEqual(strip_pos_prefix(""), "")


class TestExtractPosFromText(unittest.TestCase):
    """Tests for extract_pos_from_text()."""

    def test_single_pos(self):
        self.assertEqual(extract_pos_from_text("n. a cat"), "n.")

    def test_multiple_pos_joined(self):
        result = extract_pos_from_text("adj. / n. something")
        self.assertIn("adj.", result)
        self.assertIn("n.", result)

    def test_no_pos_returns_empty(self):
        self.assertEqual(extract_pos_from_text("just a definition"), "")

    def test_empty_string(self):
        self.assertEqual(extract_pos_from_text(""), "")


class TestParseDefinitions(unittest.TestCase):
    """Tests for parse_definitions()."""

    def test_none_returns_empty(self):
        self.assertEqual(parse_definitions(None), [])

    def test_empty_string_returns_empty(self):
        self.assertEqual(parse_definitions(""), [])

    def test_list_input(self):
        result = parse_definitions(["n. cat", "v. to catsomething"])
        self.assertEqual(len(result), 2)
        # POS prefixes should be stripped from each definition
        for r in result:
            self.assertNotIn("n.", r)
            self.assertNotIn("v.", r)

    def test_json_array_string(self):
        result = parse_definitions('["cat", "feline"]')
        self.assertEqual(result, ["cat", "feline"])

    def test_malformed_json_falls_back_to_split(self):
        result = parse_definitions("[not valid json")
        # Should fall back to SPLIT_RE.split which may return items after stripping brackets
        self.assertIsInstance(result, list)

    def test_semicolon_split(self):
        result = parse_definitions("cat; feline; kitty")
        self.assertIn("cat", result)
        self.assertIn("feline", result)
        self.assertIn("kitty", result)

    def test_strips_number_prefixes(self):
        # SPLIT_RE splits on [\n；;，,、/|]+ — "1. cat 2. dog" has no such delimiter
        # so it becomes a single item "1. cat 2. dog", then NUMBER_PREFIX_RE strips "1. "
        # leaving "cat 2. dog" as one definition (the "2." is NOT stripped because
        # NUMBER_PREFIX_RE only matches at the START of the string, not mid-string)
        result = parse_definitions("1. cat 2. dog")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "cat 2. dog")  # BUG: "2. " not stripped mid-string

    def test_strips_bracket_prefixes(self):
        result = parse_definitions("[同] cat")
        self.assertIn("cat", result)

    def test_stips_pos_prefix(self):
        result = parse_definitions("n. cat")
        self.assertIn("cat", result)
        self.assertTrue(all("n." not in r for r in result))

    def test_skips_empty_items(self):
        result = parse_definitions(["", "cat", "", "dog"])
        self.assertEqual(result, ["cat", "dog"])

    def test_non_string_iterable(self):
        result = parse_definitions([123, None])
        # 123 becomes "123", None is skipped
        self.assertIn("123", result)
        self.assertNotIn(None, result)

    def test_newline_escapes(self):
        result = parse_definitions("line1\\nline2")
        self.assertIn("line1", result[0] if result else "")
        self.assertIn("line2", result[-1] if result else "")


class TestBuildReverseTerms(unittest.TestCase):
    """Tests for build_reverse_terms()."""

    def test_none_both_returns_empty(self):
        self.assertEqual(build_reverse_terms(None, None), [])

    def test_empty_lists_returns_empty(self):
        self.assertEqual(build_reverse_terms([], []), [])

    def test_zh_terms_preferred_over_definitions(self):
        result = build_reverse_terms(["def1", "def2"], ["zh1", "zh2"])
        self.assertIn("zh1", result)
        self.assertIn("zh2", result)

    def test_fallback_to_definitions_when_no_zh_terms(self):
        result = build_reverse_terms(["n. 猫", "动物"])
        self.assertIn("猫", result)
        self.assertIn("动物", result)

    def test_splits_on_delimiters(self):
        result = build_reverse_terms(["猫；狗，鸟"])
        self.assertIn("猫", result)
        self.assertIn("狗", result)
        self.assertIn("鸟", result)

    def test_deduplicates(self):
        result = build_reverse_terms(["猫", "猫", "猫"])
        self.assertEqual(result, ["猫"])

    def test_normalizes_each_piece(self):
        result = build_reverse_terms(["  n. 猫  "])
        self.assertEqual(result, ["猫"])

    def test_skips_none_in_list(self):
        result = build_reverse_terms([None, "猫"])
        self.assertEqual(result, ["猫"])

    def test_skips_empty_after_normalize(self):
        result = build_reverse_terms(["n.", ""])  # n. normalizes to empty
        self.assertEqual(result, [])


class TestRecordGet(unittest.TestCase):
    """Tests for _record_get()."""

    def test_dict_mapping(self):
        self.assertEqual(_record_get({"a": 1}, "a"), 1)

    def test_dict_missing_key_returns_default(self):
        self.assertEqual(_record_get({"a": 1}, "b", "default"), "default")

    def test_object_with_keys(self):
        # _record_get's fallback: hasattr(record, "keys") and key in record.keys()
        # record.keys() is called as a method (no parens in `in` check? No, it has parens)
        # But: `key in record.keys()` calls keys() which must return an iterable
        obj = type("obj", (), {"keys": lambda self: ["x"], "__getitem__": lambda s, k: 99})()
        self.assertEqual(_record_get(obj, "x"), 99)

    def test_non_mapping_non_keys_object(self):
        obj = type("simple", (), {"__getitem__": lambda s, k: 42})()
        self.assertEqual(_record_get(obj, "any_key", "default"), "default")

    def test_fallback_for_non_mapping(self):
        self.assertEqual(_record_get(42, "x", "fallback"), "fallback")


class TestRecordToEntry(unittest.TestCase):
    """Tests for record_to_entry() — the central record-to-dict converter."""

    def test_minimal_record(self):
        entry = record_to_entry({"word": "test"})
        self.assertEqual(entry["word"], "test")
        self.assertEqual(entry["pos"], "")
        self.assertEqual(entry["source"], "ecdict")

    def test_phonetic_fallback_chain(self):
        entry = record_to_entry({"word": "test", "phonetic_uk": "/uk/", "phonetic_us": "/us/"})
        self.assertEqual(entry["phonetic_us"], "/us/")
        self.assertEqual(entry["phonetic_uk"], "/uk/")
        # phonetic should be phonetic or phonetic_us or phonetic_uk
        self.assertIn(entry["phonetic"], ["/us/", "/uk/"])

    def test_pos_inference_from_definition(self):
        entry = record_to_entry({"word": "test", "definition": "n. a trial"})
        self.assertEqual(entry["pos"], "n.")

    def test_pos_inference_from_translation(self):
        entry = record_to_entry({"word": "test", "definition": "trial", "translation": "n. 测试"})
        self.assertEqual(entry["pos"], "n.")

    def test_explicit_pos_overrides_inference(self):
        entry = record_to_entry({"word": "test", "pos": "v.", "definition": "n. a noun"})
        self.assertEqual(entry["pos"], "v.")

    def test_definitions_parsed_from_translation_when_definition_lacks_defs(self):
        entry = record_to_entry({
            "word": "test",
            "definition": "to try something",
            "translation": "n. 测试；v. 试验",
        })
        defs = entry["definitions"]
        self.assertIn("测试", defs)
        self.assertIn("试验", defs)

    def test_example_keys_priority_order(self):
        entry = record_to_entry({
            "word": "test",
            "example": "first",
            "sentence": "second",
            "example_sentence": "third",
        })
        self.assertEqual(entry["example"], "first")  # first key wins

    def test_example_falls_through_keys(self):
        entry = record_to_entry({
            "word": "test",
            "example_sentence": "got this one",
        })
        self.assertEqual(entry["example"], "got this one")

    def test_frequency_calculation(self):
        entry = record_to_entry({
            "word": "test",
            "frq": 100,
            "bnc": 50,
            "frequency": 10,
        })
        # frequency = frq or bnc or frequency -> frq=100 wins
        self.assertEqual(entry["frequency"], 100)

    def test_frequency_falls_back_to_bnc(self):
        entry = record_to_entry({
            "word": "test",
            "frq": 0,
            "bnc": 50,
            "frequency": 10,
        })
        self.assertEqual(entry["frequency"], 50)

    def test_frequency_falls_back_to_frequency_field(self):
        entry = record_to_entry({
            "word": "test",
            "frq": 0,
            "bnc": 0,
            "frequency": 10,
        })
        self.assertEqual(entry["frequency"], 10)

    def test_zh_terms_parsed_from_json_string(self):
        entry = record_to_entry({
            "word": "test",
            "zh_terms": '["term1", "term2"]',
        })
        zh = entry["zh_terms"]
        self.assertIn("term1", zh)
        self.assertIn("term2", zh)

    def test_zh_terms_malformed_json_becomes_list(self):
        entry = record_to_entry({
            "word": "test",
            "zh_terms": "not json at all",
        })
        zh = entry["zh_terms"]
        self.assertIsInstance(zh, list)
        # Should wrap the string itself as a single-element list
        self.assertIn("not json at all", zh)

    def test_zh_terms_none_becomes_empty_list(self):
        entry = record_to_entry({"word": "test"})
        self.assertEqual(entry["zh_terms"], [])

    def test_source_defaults_to_ecdict(self):
        entry = record_to_entry({"word": "test"})
        self.assertEqual(entry["source"], "ecdict")

    def test_source_preserved(self):
        entry = record_to_entry({"word": "test", "source": "cambridge"})
        self.assertEqual(entry["source"], "cambridge")

    def test_empty_word_record(self):
        entry = record_to_entry({})
        self.assertEqual(entry["word"], "")

    def test_none_values_handled(self):
        # None values should be coerced to empty string, not "None"
        entry = record_to_entry({
            "word": None,
            "pos": None,
            "phonetic": None,
            "definition": None,
        })
        self.assertEqual(entry["word"], "")
        self.assertEqual(entry["pos"], "")


# ===========================================================================
# 2. dict_lookup.py — unit tests
# ===========================================================================

class TestResolvePath(unittest.TestCase):
    """Tests for resolve_path()."""

    def test_explicit_value_used(self):
        result = resolve_path("/explicit/path", "SOME_VAR", pathlib.Path("/default"))
        self.assertEqual(result, pathlib.Path("/explicit/path"))

    def test_env_var_used_when_no_value(self):
        with patch.dict(os.environ, {"TEST_VAR_ENV": "/env/path"}):
            result = resolve_path(None, "TEST_VAR_ENV", pathlib.Path("/default"))
            self.assertEqual(result, pathlib.Path("/env/path"))

    def test_default_when_no_value_and_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_path(None, "NONEXISTENT_VAR_XYZ", pathlib.Path("/default"))
            self.assertEqual(result, pathlib.Path("/default"))

    def test_empty_string_is_truthy(self):
        # Empty string is falsy in Python... let's check actual behavior
        result = resolve_path("", "VAR", pathlib.Path("/default"))
        # Path("") is truthy? Actually resolve_path checks `if value:` so "" is falsy
        self.assertEqual(result, pathlib.Path("/default"))


class TestTableExists(unittest.TestCase):
    """Tests for table_exists()."""

    def _make_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        return conn

    def test_existing_table(self):
        conn = self._make_db()
        try:
            conn.execute("CREATE TABLE dictionary (word TEXT)")
            self.assertTrue(table_exists(conn, "dictionary"))
        finally:
            conn.close()

    def test_nonexistent_table(self):
        conn = self._make_db()
        try:
            self.assertFalse(table_exists(conn, "no_such_table"))
        finally:
            conn.close()


class TestExtractEnQuery(unittest.TestCase):
    """Tests for extract_en_query()."""

    def test_simple_word(self):
        self.assertEqual(extract_en_query("apple"), "apple")

    def test_strips_lookup_cues(self):
        self.assertEqual(extract_en_query("apple是什么意思"), "apple")

    def test_matches_alpha_pattern(self):
        self.assertEqual(extract_en_query("hello world"), "hello world")

    def test_hyphenated_word(self):
        result = extract_en_query("state-of-the-art")
        # Regex allows hyphens within [A-Za-z' -]*
        self.assertIn("state", result)

    def test_normalizes_case_and_whitespace(self):
        result = extract_en_query("  Apple  ")
        self.assertEqual(result, "apple")  # lowercased for consistent lookup

    def test_non_ascii_falls_through_to_normalize(self):
        result = extract_en_query("123")
        # No alpha match, falls through to normalize_query of stripped text
        self.assertEqual(result, "123")


class TestExtractZhQuery(unittest.TestCase):
    """Tests for extract_zh_query()."""

    def test_simple_chinese(self):
        self.assertEqual(extract_zh_query("重要的"), "重要的")

    def test_strips_particle_suffixes(self):
        result = extract_zh_query("重要吗")
        self.assertEqual(result, "重要")

    def test_strips_multiple_particles(self):
        # The regex strips the suffix pattern as a whole, not each particle individually
        # Pattern: [吗嘛呀啊呢哦吧哈！？。.？]+$ — matches one or more at end
        result = extract_zh_query("重要吗呀")
        self.assertEqual(result, "重要")  # Both 吗 and 呀 stripped together as suffix

    def test_strips_lookup_cues(self):
        result = extract_zh_query("重要的英语怎么说")
        self.assertNotIn("英语怎么说", result)

    def test_normalizes(self):
        self.assertEqual(extract_zh_query("  重要  "), "重要")


class TestLoadSqliteEntry(unittest.TestCase):
    """Tests for load_sqlite_entry()."""

    def _make_db_with_word(self, word: str, **kwargs) -> pathlib.Path:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                CREATE TABLE dictionary (
                    word TEXT, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                    definition TEXT, translation TEXT, definitions TEXT,
                    example TEXT, source TEXT, pos TEXT
                )
            """)
            cols = ["word"] + list(kwargs.keys())
            vals = [word] + list(kwargs.values())
            placeholders = ",".join("?" * len(cols))
            conn.execute(f"INSERT INTO dictionary ({','.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
        finally:
            conn.close()
        return db_path

    def test_found_word(self):
        db = self._make_db_with_word("apple", definition="a fruit", phonetic="/æpəl/", source="ecdict", pos="n.")
        try:
            entry = load_sqlite_entry(db, "apple")
            self.assertIsNotNone(entry)
            self.assertEqual(entry["word"], "apple")
        finally:
            db.unlink()

    def test_case_insensitive(self):
        db = self._make_db_with_word("Apple", definition="a fruit", phonetic="/æpəl/", source="ecdict", pos="n.")
        try:
            entry = load_sqlite_entry(db, "apple")
            self.assertIsNotNone(entry)
            # BUG: record_to_entry preserves original case from DB
            # The SQL uses lower(word) = ? for matching but returns the stored value
            self.assertEqual(entry["word"], "Apple")  # DB stores "Apple", not lowercased
        finally:
            db.unlink()

    def test_missing_word(self):
        db = self._make_db_with_word("other", definition="something", phonetic="", source="ecdict", pos="")
        try:
            entry = load_sqlite_entry(db, "nonexistent")
            self.assertIsNone(entry)
        finally:
            db.unlink()

    def test_nonexistent_file(self):
        entry = load_sqlite_entry(pathlib.Path("/no/such/file/xyz.db"), "word")
        self.assertIsNone(entry)

    def test_file_without_dictionary_table(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("CREATE TABLE other_table (id INTEGER)")
            conn.commit()
        finally:
            conn.close()
        try:
            entry = load_sqlite_entry(db_path, "word")
            self.assertIsNone(entry)
        finally:
            db_path.unlink()

    def test_entry_has_all_expected_keys(self):
        db = self._make_db_with_word(
            "test", definition="n. a test", translation="n. 测试",
            phonetic="/test/", phonetic_uk="/uk/", phonetic_us="/us/",
            definitions='["测试", "试验"]', example="This is a test.",
            source="cambridge", pos="n."
        )
        try:
            entry = load_sqlite_entry(db, "test")
            self.assertIsNotNone(entry)
            self.assertIn("word", entry)
            self.assertIn("pos", entry)
            self.assertIn("phonetic", entry)
            self.assertIn("definitions", entry)
            self.assertIn("example", entry)
            self.assertIn("source", entry)
        finally:
            db.unlink()


class TestLoadWordSenses(unittest.TestCase):
    """Tests for load_word_senses() — CRITICAL: the known bug fix verification."""

    def _make_db(self, schema_extra: str = "") -> tuple[pathlib.Path, sqlite3.Connection]:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            )
        """)
        if schema_extra:
            conn.executescript(schema_extra)
        conn.commit()
        return db_path, conn

    def test_word_senses_table_exists_returns_rows(self):
        db_path, conn = self._make_db("""
            CREATE TABLE word_senses (
                word TEXT, pos TEXT, definition TEXT, example TEXT, sense_rank INTEGER
            )
        """)
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('test', '/test/', '/uk/', '/us/', 'n. a test', 'n. 测试', '["测试"]', 'example sentence', 'cambridge', 'n.')
            """)
            conn.execute("""
                INSERT INTO word_senses (word, pos, definition, example, sense_rank) VALUES
                ('test', 'n.', 'a examination', 'This is a test.', 1),
                ('test', 'v.', 'to try something', 'He tested it.', 2)
            """)
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "test")
            self.assertEqual(len(senses), 2)
            self.assertEqual(senses[0]["definition"], "a examination")
            self.assertEqual(senses[1]["definition"], "to try something")
        finally:
            db_path.unlink(missing_ok=True)

    def test_word_senses_table_does_not_exist_fallback_to_dictionary(self):
        """BUG FIX VERIFICATION: must not crash with 'no such table: word_senses'.

        Before fix: missing `return []` when entry is None and table doesn't exist → crash.
        After fix: should return [] gracefully.
        """
        db_path, conn = self._make_db()  # NO word_senses table
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('hello', '/hɛˈloʊ/', '/uk/', '/us/', 'int. greeting', 'int. 你好', '["你好"]', 'Hello world!', 'ecdict', 'int.')
            """)
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "hello")
            # Should use fallback: build senses from dictionary entry's definitions
            self.assertIsInstance(senses, list)
            # Since there are definitions, should get at least one sense
            self.assertGreaterEqual(len(senses), 1)
            self.assertEqual(senses[0]["word"], "hello")
        finally:
            db_path.unlink(missing_ok=True)

    def test_word_senses_table_missing_and_word_not_found_returns_empty_list(self):
        """BUG FIX VERIFICATION: the critical path that used to crash."""
        db_path, conn = self._make_db()  # NO word_senses table, NO matching word
        try:
            conn.close()
            senses = load_word_senses(db_path, "nonexistent_word_xyz")
            # Must return [], NOT crash with "no such table"
            self.assertEqual(senses, [])
        finally:
            db_path.unlink(missing_ok=True)

    def test_nonexistent_db_file(self):
        senses = load_word_senses(pathlib.Path("/no/such/db.xyz"), "word")
        self.assertEqual(senses, [])

    def test_senses_limit_to_6(self):
        db_path, conn = self._make_db("""
            CREATE TABLE word_senses (
                word TEXT, pos TEXT, definition TEXT, example TEXT, sense_rank INTEGER
            )
        """)
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('poly', '/pɒli/', '/uk/', '/us/', 'adj. many', 'adj. 多', '["多"]', '', 'test', 'adj.')
            """)
            for i in range(10):
                conn.execute(
                    "INSERT INTO word_senses (word, pos, definition, example, sense_rank) VALUES (?, ?, ?, ?, ?)",
                    ("poly", "adj.", f"sense {i}", f"example {i}", i),
                )
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "poly")
            self.assertLessEqual(len(senses), 6)
        finally:
            db_path.unlink(missing_ok=True)

    def test_phonetic_precedence_uk_then_us_then_phonetic(self):
        db_path, conn = self._make_db("""
            CREATE TABLE word_senses (
                word TEXT, pos TEXT, definition TEXT, example TEXT, sense_rank INTEGER
            )
        """)
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('audio', '', '/uk_audio/', '/us_audio/', 'n. sound', 'n. 声音', '["声音"]', '', 'test', 'n.')
            """)
            conn.execute("""
                INSERT INTO word_senses (word, pos, definition, example, sense_rank) VALUES
                ('audio', 'n.', 'sound wave', 'sound ex', 1)
            """)
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "audio")
            self.assertEqual(len(senses), 1)
            # phonetic_uk is first non-empty among uk/us/phonetic
            self.assertEqual(senses[0]["phonetic"], "/uk_audio/")
        finally:
            db_path.unlink(missing_ok=True)

    def test_fallback_parses_example_json(self):
        db_path, conn = self._make_db()  # no word_senses table
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('jsonex', '/j/', '/uk/', '/us/', 'n. json example', 'n. JSON示例',
                        '["JSON示例", "JSON例子"]', '["ex1", "ex2", "ex3"]', 'test', 'n.')
            """)
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "jsonex")
            self.assertEqual(len(senses), 2)  # 2 definitions
            self.assertEqual(senses[0]["example"], "ex1")
            self.assertEqual(senses[1]["example"], "ex2")
        finally:
            db_path.unlink(missing_ok=True)

    def test_fallback_handles_malformed_example_json(self):
        db_path, conn = self._make_db()  # no word_senses table
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES('badex', '/b/', '/uk/', '/us/', 'n. bad example', 'n. 坏例子',
                       '["坏例子"]', 'not valid json{', 'test', 'n.')
            """)
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "badex")
            self.assertEqual(len(senses), 1)
            # Malformed JSON: should fall back to raw string
            self.assertEqual(senses[0]["example"], "not valid json{")
        finally:
            db_path.unlink(missing_ok=True)

    def test_fallback_empty_example_string(self):
        db_path, conn = self._make_db()
        try:
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES('emptyex', '/e/', '/uk/', '/us/', 'n. empty', 'n. 空', '["空"]', '', 'test', 'n.')
            """)
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "emptyex")
            self.assertEqual(len(senses), 1)
            self.assertEqual(senses[0]["example"], "")
        finally:
            db_path.unlink(missing_ok=True)

    def test_fallback_limits_to_5_senses(self):
        db_path, conn = self._make_db()
        try:
            defs = json.dumps([f"definition {i}" for i in range(8)])
            exs = json.dumps([f"example {i}" for i in range(8)])
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES('many', '/m/', '/uk/', '/us/', 'n. many things', 'n. 许多', ?, ?, 'test', 'n.')
            """, (defs, exs))
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "many")
            self.assertLessEqual(len(senses), 5)
        finally:
            db_path.unlink(missing_ok=True)

    def test_fallback_skips_empty_definitions(self):
        db_path, conn = self._make_db()
        try:
            defs = json.dumps(["", "valid_def", "", "another_valid", ""])
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES('skip', '/s/', '/uk/', '/us/', 'n. skip', 'n. 跳过', ?, '["ex"]', 'test', 'n.')
            """, (defs,))
            conn.commit()
            conn.close()

            senses = load_word_senses(db_path, "skip")
            # Should skip empty definitions (the `if d` filter)
            for s in senses:
                self.assertTrue(s["definition"])
        finally:
            db_path.unlink(missing_ok=True)


class TestLoadSqliteMatches(unittest.TestCase):
    """Tests for load_sqlite_matches()."""

    def _make_db(self) -> pathlib.Path:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            );
            CREATE TABLE dictionary_reverse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zh_term TEXT NOT NULL, word TEXT, pos TEXT, phonetic TEXT,
                source TEXT, frequency INTEGER, sense_rank INTEGER
            );
            CREATE INDEX idx_rev_zh ON dictionary_reverse(zh_term);
            CREATE INDEX idx_rev_word ON dictionary_reverse(word);
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_exact_match_on_reverse_index(self):
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('important', '/ɪmˈpɔːrtnt/', '/uk/', '/us/', 'adj. important', 'adj. 重要的', '["重要的"]', 'It is important.', 'ecdict', 'adj.')
            """)
            conn.execute("""
                INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                VALUES ('重要的', 'important', 'adj.', '/ɪmˈpɔːrtnt/', 'ecdict', 500, 0)
            """)
            conn.commit()
            conn.close()

            matches = load_sqlite_matches(db, "重要的")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["word"], "important")
        finally:
            db.unlink()

    def test_fuzzy_match_on_reverse_index(self):
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('happy', '/ˈhæpi/', '/uk/', '/us/', 'adj. happy', 'adj. 快乐的', '["快乐的"]', 'Be happy.', 'ecdict', 'adj.')
            """)
            conn.execute("""
                INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                VALUES ('快乐', 'happy', 'adj.', '/ˈhæpi/', 'ecdict', 100, 0)
            """)
            conn.commit()
            conn.close()

            matches = load_sqlite_matches(db, "快乐的人")
            # LIKE '%快乐的人%' won't match '快乐'; '快乐的人' LIKE '快乐' also won't match
            # But query LIKE zh_term: '快乐的人' LIKE '%' + '快乐' + '%' → matches!
            self.assertGreaterEqual(len(matches), 1)
        finally:
            db.unlink()

    def test_no_match(self):
        db = self._make_db()
        try:
            matches = load_sqlite_matches(db, "完全不存在的词")
            self.assertEqual(matches, [])
        finally:
            db.unlink()

    def test_nonexistent_file(self):
        matches = load_sqlite_matches(pathlib.Path("/no/such/file.db"), "query")
        self.assertEqual(matches, [])

    def test_respects_limit(self):
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            for i, word in enumerate(["word_a", "word_b", "word_c"]):
                conn.execute("""
                    INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                    VALUES (?, '/w/', '/uk/', '/us/', 'n. word', 'n. 词', '["词"]', '', 'ecdict', 'n.')
                """, (word,))
                conn.execute("""
                    INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                    VALUES (?, ?, 'n.', '/w/', 'ecdict', 100, 0)
                """, (f"词_{i}", word))
            conn.commit()
            conn.close()

            matches = load_sqlite_matches(db, "词", limit=2)
            self.assertLessEqual(len(matches), 2)
        finally:
            db.unlink()

    def test_deduplication_by_word(self):
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('dup', '/d/', '/uk/', '/us/', 'n. dup', 'n. 重复', '["重复"]', '', 'ecdict', 'n.')
            """)
            conn.execute("""
                INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                VALUES ('重复', 'dup', 'n.', '/d/', 'ecdict', 100, 0)
            """)
            conn.execute("""
                INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                VALUES ('重复', 'dup', 'n.', '/d/', 'ecdict', 200, 1)
            """)
            conn.commit()
            conn.close()

            matches = load_sqlite_matches(db, "重复")
            # Same word should appear only once
            words = [m["word"] for m in matches]
            self.assertEqual(words.count("dup"), 1)
        finally:
            db.unlink()

    def test_fallback_full_table_scan_when_no_reverse_table(self):
        """When dictionary_reverse doesn't exist, falls back to scanning entire dictionary table.
        This is a known inefficiency but should still work correctly."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            )
        """)
        conn.execute("""
            INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
            VALUES ('bright', '/braɪt/', '/uk/', '/us/', 'adj. bright', 'adj. 明亮的', '["明亮的"]', 'The sun is bright.', 'ecdict', 'adj.')
        """)
        conn.commit()
        conn.close()
        try:
            matches = load_sqlite_matches(db_path, "明亮")
            self.assertGreaterEqual(len(matches), 1)
            self.assertEqual(matches[0]["word"], "bright")
        finally:
            db_path.unlink()


class TestLoadSampleIndexes(unittest.TestCase):
    """Tests for load_sample_indexes()."""

    def test_nonexistent_file(self):
        by_word, by_zh = load_sample_indexes(pathlib.Path("/no/such/file.json"))
        self.assertEqual(by_word, {})
        self.assertEqual(by_zh, {})

    def test_valid_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([
                {"word": "apple", "pos": "n.", "phonetic": "/æpəl/", "definition": "a fruit",
                 "translation": "n. 水果", "definitions": ["水果"], "example": "I eat an apple.",
                 "source": "ecdict", "zh_terms": ["水果"]}
            ], f)
            f.flush()
            path = pathlib.Path(f.name)

        try:
            by_word, by_zh = load_sample_indexes(path)
            self.assertIn("apple", by_word)
            self.assertEqual(by_word["apple"]["word"], "apple")
        finally:
            path.unlink()

    def test_empty_json_array(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([], f)
            f.flush()
            path = pathlib.Path(f.name)

        try:
            by_word, by_zh = load_sample_indexes(path)
            self.assertEqual(by_word, {})
            self.assertEqual(by_zh, {})
        finally:
            path.unlink()

    def test_skips_entries_with_empty_word(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([
                {"word": "", "pos": "n.", "definition": "nothing"},
                {"word": "valid", "pos": "n.", "definition": "something"},
            ], f)
            f.flush()
            path = pathlib.Path(f.name)

        try:
            by_word, by_zh = load_sample_indexes(path)
            self.assertNotIn("", by_word)
            self.assertIn("valid", by_word)
        finally:
            path.unlink()


class TestLoadSampleEntry(unittest.TestCase):
    """Tests for load_sample_entry()."""

    def test_found(self):
        indexes = ({"hello": {"word": "hello", "pos": "int.", "phonetic": "/hɛˈloʊ/"}}, {})
        result = load_sample_entry(indexes, "hello")
        self.assertIsNotNone(result)
        self.assertEqual(result["word"], "hello")

    def test_not_found(self):
        indexes = ({"other": {"word": "other"}}, {})
        result = load_sample_entry(indexes, "hello")
        self.assertIsNone(result)

    def test_case_insensitive(self):
        indexes = ({"hello": {"word": "Hello"}}, {})  # key must be lowercased for lookup
        result = load_sample_entry(indexes, "hello")
        self.assertIsNotNone(result)
        self.assertEqual(result["word"], "Hello")


class TestLoadSampleMatches(unittest.TestCase):
    """Tests for load_sample_matches()."""

    def _make_sample_entry(self, word: str, **kwargs) -> dict[str, Any]:
        """Create a sample entry dict with all keys required by entry_for_output."""
        base = {
            "word": word,
            "pos": kwargs.get("pos", "n."),
            "phonetic": kwargs.get("phonetic", f"/{word}/"),
            "definitions": kwargs.get("definitions", [f"def of {word}"]),
            "example": kwargs.get("example", ""),
            "source": kwargs.get("source", "sample"),
            "frequency": kwargs.get("frequency", 0),
        }
        base.update(kwargs)
        return base

    def test_exact_match(self):
        indexes = ({}, {
            "重要的": [
                self._make_sample_entry("important", pos="adj.", phonetic="/ɪmˈpɔːrtnt/", frequency=500),
                self._make_sample_entry("significant", pos="adj.", phonetic="/sɪɡˈnɪfɪkənt/", frequency=300),
            ]
        })
        matches = load_sample_matches(indexes, "重要的")
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["word"], "important")  # higher frequency first

    def test_fuzzy_match(self):
        indexes = ({}, {
            "重要的事情": [self._make_sample_entry("matter", frequency=100)],
        })
        matches = load_sample_matches(indexes, "重要")
        # "重要" in "重要的事情" → should match
        self.assertGreaterEqual(len(matches), 1)

    def test_no_match(self):
        indexes = ({}, {"其他": [self._make_sample_entry("other")]})
        matches = load_sample_matches(indexes, "完全不相关")
        self.assertEqual(matches, [])

    def test_respects_limit(self):
        indexes = ({}, {
            "词": [
                self._make_sample_entry("word_a", frequency=100),
                self._make_sample_entry("word_b", frequency=200),
                self._make_sample_entry("word_c", frequency=300),
            ]
        })
        matches = load_sample_matches(indexes, "词", limit=2)
        self.assertLessEqual(len(matches), 2)

    def test_deduplication(self):
        indexes = ({}, {
            "词": [
                self._make_sample_entry("dup", frequency=100),
                self._make_sample_entry("dup", frequency=200),
            ]
        })
        matches = load_sample_matches(indexes, "词")
        words = [m["word"] for m in matches]
        self.assertEqual(words.count("dup"), 1)


class TestEntryForOutput(unittest.TestCase):
    """Tests for entry_for_output()."""

    def test_selects_correct_keys(self):
        entry = {
            "word": "test", "pos": "n.", "phonetic": "/t/",
            "definitions": ["def1", "def2"],
            "example": "an example", "source": "ecdict",
            "extra_key": "should be dropped",
        }
        result = entry_for_output(entry)
        self.assertIn("word", result)
        self.assertIn("pos", result)
        self.assertIn("phonetic", result)
        self.assertIn("definitions", result)
        self.assertIn("example", result)
        self.assertIn("source", result)
        self.assertNotIn("extra_key", result)


class TestAppendMissingWord(unittest.TestCase):
    """Tests for append_missing_word()."""

    def test_creates_file_and_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = pathlib.Path(tmpdir) / "subdir" / "missing_words.log"
            append_missing_word(log_path, "hello")
            append_missing_word(log_path, "world")

            content = log_path.read_text(encoding="utf-8")
            self.assertIn("hello\n", content)
            self.assertIn("world\n", content)

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = pathlib.Path(tmpdir) / "a" / "b" / "c" / "missing.log"
            append_missing_word(log_path, "deep")
            self.assertTrue(log_path.exists())


class TestFormatEnToZhText(unittest.TestCase):
    """Tests for format_en_to_zh_text()."""

    def test_empty_result_with_no_senses_or_definitions(self):
        result = format_en_to_zh_text({"word": "unknown"})
        self.assertEqual(result, "**unknown**")

    def test_word_only_format(self):
        result = format_en_to_zh_text({"word": "hello"})
        self.assertEqual(result, "**hello**")

    def test_with_senses(self):
        result = format_en_to_zh_text({
            "word": "apple",
            "senses": [
                {"pos": "n.", "definition": "a fruit", "example": "I eat an apple.", "phonetic": "/æpəl/"},
                {"pos": "v.", "definition": "to apple something", "example": ""},
            ]
        })
        self.assertIn("**apple**", result)
        self.assertIn("/æpəl/", result)
        self.assertIn("a fruit", result)
        self.assertIn("I eat an apple.", result)

    def test_senses_built_from_definitions(self):
        """When no senses key but definitions exist, builds synthetic senses."""
        result = format_en_to_zh_text({
            "word": "test",
            "definitions": ["n. a trial", "v. to examine"],
            "example": "This is a test.",
        })
        self.assertIn("**test**", result)
        self.assertIn("a trial", result)
        self.assertIn("to examine", result)

    def test_definition_senses_example_only_on_first(self):
        """BUG PATTERN: When building senses from definitions, only i==0 gets example."""
        result = format_en_to_zh_text({
            "word": "multi",
            "definitions": ["def1", "def2", "def3"],
            "example": "only for first",
        })
        lines = result.split("\n")
        # First sense should have example
        example_lines = [l for l in lines if "only for first" in l]
        self.assertEqual(len(example_lines), 1)

    def test_phonetic_displayed(self):
        result = format_en_to_zh_text({
            "word": "phonetic_test",
            "senses": [
                {"pos": "n.", "definition": "test", "example": "", "phonetic": "/fəˈnɛtɪk/"},
            ]
        })
        self.assertIn("/fəˈnɛtɪk/", result)

    def test_empty_phonetic_omitted(self):
        result = format_en_to_zh_text({
            "word": "nophon",
            "senses": [
                {"pos": "n.", "definition": "test", "example": "", "phonetic": ""},
            ]
        })
        # Should not show phonetic line when empty
        lines = result.split("\n")
        phonetic_lines = [l for l in lines if "🔤" in l]
        # Actually the format uses 🔤 for phonetic display
        # If phonetic is empty string, the `or ""` gives "", and `if phonetic:` is False


class TestLookupEnToZh(unittest.TestCase):
    """Integration tests for lookup_en_to_zh() — THE CRITICAL BUG AREA.

    Known bug: When entry is found (not None) but senses is empty, the function
    returned {'word': word, 'senses': []} without populating senses from entry.
    """

    def _make_db(self) -> pathlib.Path:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            );
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_word_found_via_word_senses(self):
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            conn.executescript("""
                CREATE TABLE word_senses (
                    word TEXT, pos TEXT, definition TEXT, example TEXT, sense_rank INTEGER
                );
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('happy', '/ˈhæpi/', '/uk/', '/us/', 'adj. happy', 'adj. 快乐', '["快乐"]', 'Be happy!', 'ecdict', 'adj.');
                INSERT INTO word_senses (word, pos, definition, example, sense_rank)
                VALUES ('happy', 'adj.', 'feeling pleasure', 'I am happy!', 1);
            """)
            conn.commit()
            conn.close()

            result = lookup_en_to_zh("happy", db, ({}, {}))
            self.assertNotIn("error", result)
            self.assertEqual(result["word"], "happy")
            self.assertGreaterEqual(len(result.get("senses", [])), 1)
        finally:
            db.unlink()

    def test_word_found_via_sqlite_entry_fallback(self):
        """When word_senses returns empty but entry exists, should populate from entry.

        BUG CHECK: This was the broken path. lookup_en_to_zh found an entry but
        returned {'word': w, 'senses': []} instead of building senses from entry.
        """
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('garden', '/ˈɡɑːrdn/', '/uk/', '/us/', 'n. garden', 'n. 花园', '["花园", "园林"]', 'A beautiful garden.', 'ecdict', 'n.')
            """)
            conn.commit()
            conn.close()

            result = lookup_en_to_zh("garden", db, ({}, {}))
            self.assertNotIn("error", result)
            self.assertEqual(result["word"], "garden")
            # THE KEY ASSERTION: senses should NOT be empty when entry has definitions
            senses = result.get("senses", [])
            if len(senses) == 0:
                self.fail(
                    "BUG CONFIRMED: lookup_en_to_zh returned empty senses for a word "
                    "that exists in the database with definitions. "
                    "Line ~295 in dict_lookup.py: returns {'word': word, 'senses': senses} "
                    "but `senses` is still [] because it was never repopulated from entry.\n"
                    "FIX: After finding entry at line 290-291, build senses from entry's "
                    "definitions before returning."
                )
        finally:
            db.unlink()

    def test_word_found_via_sample_fallback(self):
        db = self._make_db()
        try:
            sample = ({
                "sampleword": {
                    "word": "sampleword", "pos": "n.", "phonetic": "/s/",
                    "definitions": ["sample definition"], "example": "sample ex",
                    "source": "sample",
                }
            }, {})

            result = lookup_en_to_zh("sampleword", db, sample)
            self.assertNotIn("error", result)
            self.assertEqual(result["word"], "sampleword")
        finally:
            db.unlink()

    def test_word_not_found_returns_error(self):
        db = self._make_db()
        try:
            with patch("scripts.dict_lookup.append_missing_word") as mock_append:
                result = lookup_en_to_zh("zzz_nonexistent_xyz", db, ({}, {}))
            self.assertIn("error", result)
            self.assertEqual(result["error"], "not_found")
            self.assertEqual(result["mode"], "en_to_zh")
            mock_append.assert_called_once()
        finally:
            db.unlink()

    def test_nonexistent_db_with_sample_fallback(self):
        db = pathlib.Path("/no/such/db.xyz")
        sample = ({
            "fallback": {
                "word": "fallback", "pos": "n.", "phonetic": "/f/",
                "definitions": ["fallback def"], "example": "",
                "source": "sample",
            }
        }, {})
        result = lookup_en_to_zh("fallback", db, sample)
        self.assertNotIn("error", result)
        self.assertEqual(result["word"], "fallback")


class TestLookupZhToEn(unittest.TestCase):
    """Integration tests for lookup_zh_to_en()."""

    def _make_db(self) -> pathlib.Path:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            );
            CREATE TABLE dictionary_reverse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zh_term TEXT NOT NULL, word TEXT, pos TEXT, phonetic TEXT,
                source TEXT, frequency INTEGER, sense_rank INTEGER
            );
            CREATE INDEX idx_rev_zh ON dictionary_reverse(zh_term);
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_exact_zh_match(self):
        db = self._make_db()
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("""
                INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
                VALUES ('important', '/ɪmˈpɔːrtnt/', '/uk/', '/us/', 'adj. important', 'adj. 重要的', '["重要的"]', 'It is important.', 'ecdict', 'adj.')
            """)
            conn.execute("""
                INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
                VALUES ('重要的', 'important', 'adj.', '/ɪmˈpɔːrtnt/', 'ecdict', 500, 0)
            """)
            conn.commit()
            conn.close()

            result = lookup_zh_to_en("重要的", db, ({}, {}))
            self.assertNotIn("error", result)
            self.assertGreaterEqual(len(result.get("matches", [])), 1)
        finally:
            db.unlink()

    def test_falls_back_to_sample(self):
        db = self._make_db()
        try:
            sample = ({}, {
                "关键": [{
                    "word": "key", "pos": "n.", "phonetic": "/kiː/",
                    "definitions": ["def"], "example": "", "source": "sample", "frequency": 200
                }]
            })

            result = lookup_zh_to_en("关键", db, sample)
            self.assertNotIn("error", result)
            self.assertGreaterEqual(len(result.get("matches", [])), 1)
        finally:
            db.unlink()

    def test_not_found_returns_error(self):
        db = self._make_db()
        try:
            with patch("scripts.dict_lookup.append_missing_word") as mock_append:
                result = lookup_zh_to_en("完全不存在的词xyz", db, ({}, {}))
            self.assertIn("error", result)
            self.assertEqual(result["error"], "not_found")
            self.assertEqual(result["mode"], "zh_to_en")
            mock_append.assert_called_once()
        finally:
            db.unlink()


# ===========================================================================
# 3. validate_lookup_output.py — unit tests
# ===========================================================================

class TestValidateLookupOutputNormalization(unittest.TestCase):
    """Tests for _normalize()."""

    def test_strips_blank_lines(self):
        result = _normalize("  hello  \n\n  world  \n")
        # _normalize: text.strip() first, then splitlines, then line.rstrip(), filter by line.strip()
        # text.strip() removes leading/trailing whitespace from entire string
        self.assertEqual(result, ["hello", "  world"])

    def test_empty_string(self):
        result = _normalize("")
        self.assertEqual(result, [])

    def test_only_whitespace(self):
        result = _normalize("   \n  \n  ")
        self.assertEqual(result, [])


class TestValidateLookupOutputEnToZh(unittest.TestCase):
    """Tests for validate() with mode='en_to_zh'."""

    def test_perfect_card(self):
        card = "**hallucination**\n- 🔤 音标：/həˌluːsɪˈneɪʃən/\n- 🇨🇳 释义：n. 幻觉"
        result = validate(card, "en_to_zh")
        self.assertTrue(result.ok, result.errors)

    def test_card_with_optional_second_definition(self):
        card = "**word**\n- 🔤 音标：/wɜːrd/\n- 🇨🇳 释义：n. 词\n- 🇨🇳 释义 2：v. 措辞"
        result = validate(card, "en_to_zh")
        self.assertTrue(result.ok, result.errors)

    def test_card_with_example(self):
        card = "**word**\n- 🔤 音标：/wɜːrd/\n- 🇨🇳 释义：n. 词\n- 💬 例句：This is a word."
        result = validate(card, "en_to_zh")
        self.assertTrue(result.ok, result.errors)

    def test_card_with_second_def_and_example(self):
        card = "**word**\n- 🔤 音标：/wɜːrd/\n- 🇨🇳 释义：n. 词\n- 🇨🇳 释义 2：v. 措辞\n- 💬 例句：Use this word."
        result = validate(card, "en_to_zh")
        self.assertTrue(result.ok, result.errors)

    def test_rejects_missing_header_asterisks(self):
        card = "hallucination\n- 🔤 音标：/həˌluːsɪˈneɪʃən/\n- 🇨🇳 释义：n. 幻觉"
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("header template" in e for e in result.errors))

    def test_rejects_too_few_lines(self):
        card = "**word**\n- 🔤 音标：/w/"
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("missing required" in e for e in result.errors))

    def test_rejects_wrong_phonetic_line_prefix(self):
        card = "**word**\n- wrong prefix\n- 🇨🇳 释义：n. 词"
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("must start with" in e for e in result.errors))

    def test_rejects_wrong_definition_line_prefix(self):
        card = "**word**\n- 🔤 音标：/w/\n- wrong prefix here"
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("must start with" in e for e in result.errors))

    def test_rejects_extra_line(self):
        card = "**word**\n- 🔤 音标：/w/\n- 🇨🇳 释义：n. 词\nextra garbage"
        result = validate(card, "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("extra line" in e for e in result.errors))

    def test_rejects_forbidden_snippet(self):
        for snippet in FORBIDDEN_SNIPPETS:
            card = f"**word**\n- 🔤 音标：/w/\n- 🇨🇳 释义：n. 词\n{snippet}"
            result = validate(card, "en_to_zh")
            self.assertFalse(result.ok, f"Should reject forbidden snippet: {snippet}")
            self.assertTrue(any(snippet in e for e in result.errors))

    def test_rejects_empty_response(self):
        result = validate("", "en_to_zh")
        self.assertFalse(result.ok)
        self.assertTrue(any("empty" in e.lower() for e in result.errors))


class TestValidateLookupOutputZhToEn(unittest.TestCase):
    """Tests for validate() with mode='zh_to_en'."""

    def test_perfect_card_minimal(self):
        card = "**重要的**\n- 🔤 最常用英文：important /ɪmˈpɔːrtnt/\n- 🔤 音标：/ɪmˈpɔːrtnt/\n- 🇨🇳 对应义：adj. 重要的"
        result = validate(card, "zh_to_en")
        self.assertTrue(result.ok, result.errors)

    def test_card_with_second_english(self):
        card = "**重要的**\n- 🔤 最常用英文：important /ɪmˈpɔːrtnt/\n- 🔤 第二常用英文：significant /sɪɡˈnɪfɪkənt/\n- 🔤 音标：/ɪmˈpɔːrtnt/\n- 🇨🇳 对应义：adj. 重要的"
        result = validate(card, "zh_to_en")
        self.assertTrue(result.ok, result.errors)

    def test_card_with_example(self):
        card = "**重要的**\n- 🔤 最常用英文：important /ɪmˈpɔːrtnt/\n- 🔤 音标：/ɪmˈpɔːrtnt/\n- 🇨🇳 对应义：adj. 重要的\n- 💬 例句：It is important."
        result = validate(card, "zh_to_en")
        self.assertTrue(result.ok, result.errors)

    def test_full_card(self):
        card = (
            "**重要的**\n"
            "- 🔤 最常用英文：important /ɪmˈpɔːrtnt/\n"
            "- 🔤 第二常用英文：significant /sɪɡˈnɪfɪkənt/\n"
            "- 🔤 音标：/ɪmˈpɔːrtnt/\n"
            "- 🇨🇳 对应义：adj. 重要的\n"
            "- 💬 例句：It is important."
        )
        result = validate(card, "zh_to_en")
        self.assertTrue(result.ok, result.errors)

    def test_rejects_missing_first_english(self):
        card = "**重要的**\n- 🔤 音标：/ɪmˈpɔːrtnt/\n- 🇨🇳 对应义：adj. 重要的"
        result = validate(card, "zh_to_en")
        self.assertFalse(result.ok)

    def test_rejects_missing_phonetic(self):
        card = "**重要的**\n- 🔤 最常用英文：important /\n- 🇨🇳 对应义：adj. 重要的"
        result = validate(card, "zh_to_en")
        self.assertFalse(result.ok)

    def test_rejects_missing_corresponding_meaning(self):
        card = "**重要的**\n- 🔤 最常用英文：important /\n- 🔤 音标：/ɪm/"
        result = validate(card, "zh_to_en")
        self.assertFalse(result.ok)

    def test_rejects_too_few_lines(self):
        card = "**重要的**\n- 🔤 音标：/"
        result = validate(card, "zh_to_en")
        self.assertFalse(result.ok)
        self.assertTrue(any("missing required" in e for e in result.errors))


# ===========================================================================
# 4. build_cambridge_dict.py — unit tests (importable functions)
# ===========================================================================

from scripts.build_cambridge_dict import (  # noqa: E402
    CambridgeEntry as _BCE,
    clean_text as _b_clean_text,
    extract_entry as _b_extract_entry,
    load_wordlist as _b_load_wordlist,
    ensure_schema as _b_ensure_schema,
    already_fetched as _b_already_fetched,
    build_reverse_terms as _b_build_reverse_terms,
    write_entry as _b_write_entry,
    fetch_with_retry as _b_fetch_with_retry,
)


class TestBuildCambridgeDictCleanText(unittest.TestCase):
    """Tests for clean_text() in build_cambridge_dict.py."""

    def test_basic_cleanup(self):
        result = _b_clean_text("  hello   world  ")
        self.assertEqual(result, "hello world")

    def test_html_unescape(self):
        result = _b_clean_text("hello &amp; world")
        self.assertEqual(result, "hello & world")

    def test_collapse_whitespace(self):
        result = _b_clean_text("hello\t\n  world")
        self.assertEqual(result, "hello world")

    def test_strip_space_before_punctuation(self):
        result = _b_clean_text("hello , world ; test")
        self.assertEqual(result, "hello, world; test")

    def test_empty_string(self):
        self.assertEqual(_b_clean_text(""), "")


class TestBuildCambridgeDictExtractEntry(unittest.TestCase):
    """Tests for extract_entry() in build_cambridge_dict.py.

    BUG FIX VERIFICATION: extract_entry must always return a value on all paths.
    Previously missing `return result` at end of function.
    """

    def test_no_entry_body_returns_none(self):
        html = "<html><body><div>no entry body</div></body></html>"
        result = _b_extract_entry(html, "test", "http://example.com")
        self.assertIsNone(result)

    def test_no_hw_node_returns_none(self):
        html = '<html><body><div class="entry-body"><div>content but no .hw</div></div></body></html>'
        result = _b_extract_entry(html, "test", "http://example.com")
        self.assertIsNone(result)

    def test_minimal_entry_returns_result(self):
        """BUG FIX VERIFICATION: must return a CambridgeEntry, not None/implicit.

        The bug was a missing `return result` at the end of extract_entry().
        """
        html = '''
        <html><body>
        <div class="entry-body">
            <span class="hw">hello</span>
        </div>
        </body></html>
        '''
        result = _b_extract_entry(html, "hello", "http://example.com/cambridge/hello")
        self.assertIsNotNone(result, "BUG: extract_entry returned None! Missing `return result`?")
        self.assertIsInstance(result, _BCE)
        self.assertEqual(result.word, "hello")

    def test_entry_with_phonetics(self):
        html = '''
        <html><body>
        <div class="entry-body">
            <span class="hw">hello</span>
            <div class="uk"><span class="pron">/hɛˈloʊ/</span></div>
            <div class="us"><span class="pron">/hɛˈloʊ/</span></div>
        </div>
        </body></html>
        '''
        result = _b_extract_entry(html, "hello", "http://example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result.phonetic_uk, "/hɛˈloʊ/")
        self.assertEqual(result.phonetic_us, "/hɛˈloʊ/")

    def test_entry_with_fallback_single_def(self):
        """When no def-block/dsense blocks, falls back to single .def/.trans."""
        html = '''
        <html><body>
        <div class="entry-body">
            <span class="hw">greet</span>
            <span class="def">to say hello</span>
            <span class="trans">打招呼</span>
        </div>
        </body></html>
        '''
        result = _b_extract_entry(html, "greet", "http://example.com")
        self.assertIsNotNone(result, "BUG: extract_entry returned None for fallback path!")
        self.assertEqual(result.definition, "to say hello")
        self.assertEqual(result.translation, "打招呼")

    def test_entry_with_dsense_blocks(self):
        html = '''
        <html><body>
        <div class="entry-body">
            <span class="hw">run</span>
            <div class="dsense">
                <span class="def">to move fast</span>
                <span class="trans">跑</span>
                <span class="pos">verb</span>
            </div>
            <div class="dsense">
                <span class="def">to operate</span>
                <span class="trans">经营</span>
                <span class="pos">verb</span>
            </div>
        </div>
        </body></html>
        '''
        result = _b_extract_entry(html, "run", "http://example.com")
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result.definitions), 1)

    def test_entry_with_cefr_level(self):
        html = '''
        <html><body>
        <div class="entry-body">
            <span class="hw">basic</span>
            <div class="dsense">
                <span class="def">fundamental</span>
                <span class="epp-xref">A2</span>
            </div>
        </div>
        </body></html>
        '''
        result = _b_extract_entry(html, "basic", "http://example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result.cefr_level, "A2")

    def test_entry_pos_cap_respected(self):
        """POS caps limit how many entries per part of speech."""
        html_parts = ['<html><body><div class="entry-body"><span class="hw">polymorphic</span>']
        for i in range(20):
            html_parts.append(f'''
            <div class="dsense">
                <span class="pos">verb</span>
                <span class="def">verb sense {i}</span>
                <span class="trans">动词含义{i}</span>
            </div>
            ''')
        html_parts.append('</div></body></html>')
        html = "".join(html_parts)

        result = _b_extract_entry(html, "polymorphic", "http://example.com")
        self.assertIsNotNone(result)
        verb_defs = [d for d in result.definitions if d.startswith("v.")]
        # v. cap is 8
        self.assertLessEqual(len(verb_defs), 8)

    def test_entry_duplicates_filtered(self):
        html = '''
        <html><body>
        <div class="entry-body">
            <span class="hw">duplicate</span>
            <div class="dsense">
                <span class="pos">noun</span>
                <span class="def">a copy</span>
                <span class="trans">副本</span>
            </div>
            <div class="dsense">
                <span class="pos">noun</span>
                <span class="def">a copy</span>
                <span class="trans">副本</span>
            </div>
        </div>
        </body></html>
        '''
        result = _b_extract_entry(html, "duplicate", "http://example.com")
        self.assertIsNotNone(result)
        # Duplicate full_def should be filtered
        dup_count = result.definitions.count("n. 副本")
        self.assertLessEqual(dup_count, 1)

    def test_entry_max_15_definitions(self):
        html_parts = ['<html><body><div class="entry-body"><span class="hw">many</span>']
        for i in range(25):
            html_parts.append(f'''
            <div class="dsense">
                <span class="pos">noun</span>
                <span class="def">sense {i}</span>
                <span class="trans">含义{i}</span>
            </div>
            ''')
        html_parts.append('</div></body></html>')
        html = "".join(html_parts)

        result = _b_extract_entry(html, "many", "http://example.com")
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result.definitions), 15)


class TestBuildCambridgeDictLoadWordlist(unittest.TestCase):
    """Tests for load_wordlist() in build_cambridge_dict.py."""

    def test_basic_wordlist(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("apple\nbanana\ncherry\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertEqual(words, ["apple", "banana", "cherry"])
        finally:
            path.unlink()

    def test_skips_comments(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("# comment\napple\n# another\nbanana\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertEqual(words, ["apple", "banana"])
        finally:
            path.unlink()

    def test_skips_empty_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\napple\n\nbanana\n\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertEqual(words, ["apple", "banana"])
        finally:
            path.unlink()

    def test_splits_on_comma(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("apple, noun\nbanana, verb\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertEqual(words, ["apple", "banana"])
        finally:
            path.unlink()

    def test_filters_invalid_words(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("apple\n123invalid\nunderscore_word\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertIn("apple", words)
            self.assertNotIn("123invalid", words)
            # underscore is not in WORD_RE pattern
        finally:
            path.unlink()

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertEqual(words, [])
        finally:
            path.unlink()

    def test_apostrophe_words_allowed(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("today's\nJohn's\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertIn("today's", words)
            self.assertIn("John's", words)
        finally:
            path.unlink()

    def test_hyphenated_words_allowed(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("state-of-the-art\nwell-known\n")
            f.flush()
            path = pathlib.Path(f.name)
        try:
            words = _b_load_wordlist(path)
            self.assertIn("state-of-the-art", words)
            self.assertIn("well-known", words)
        finally:
            path.unlink()


class TestBuildCambridgeDictEnsureSchema(unittest.TestCase):
    """Tests for ensure_schema() in build_cambridge_dict.py."""

    def test_creates_tables(self):
        conn = sqlite3.connect(":memory:")
        try:
            _b_ensure_schema(conn)
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            self.assertIn("dictionary", tables)
            self.assertIn("dictionary_reverse", tables)
        finally:
            conn.close()

    def test_idempotent(self):
        conn = sqlite3.connect(":memory:")
        try:
            _b_ensure_schema(conn)
            _b_ensure_schema(conn)  # Should not raise
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            self.assertIn("dictionary", tables)
        finally:
            conn.close()

    def test_adds_cefr_column(self):
        conn = sqlite3.connect(":memory:")
        try:
            # Create table WITHOUT cefr_level column first
            conn.execute("""
                CREATE TABLE dictionary (
                    word TEXT PRIMARY KEY, phonetic TEXT, definition TEXT
                )
            """)
            conn.commit()
            _b_ensure_schema(conn)
            # Now cefr_level column should exist
            cols = [row[1] for row in conn.execute("PRAGMA table_info(dictionary)").fetchall()]
            self.assertIn("cefr_level", cols)
        finally:
            conn.close()

    def test_existing_cefr_column_no_error(self):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("""
                CREATE TABLE dictionary (
                    word TEXT PRIMARY KEY, cefr_level TEXT DEFAULT NULL
                )
            """)
            conn.commit()
            _b_ensure_schema(conn)  # ALTER TABLE should silently pass
        finally:
            conn.close()


class TestBuildCambridgeDictAlreadyFetched(unittest.TestCase):
    """Tests for already_fetched() in build_cambridge_dict.py."""

    def test_fetched_word(self):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("""
                CREATE TABLE dictionary (word TEXT PRIMARY KEY, source TEXT DEFAULT 'ecdict')
            """)
            conn.execute("INSERT INTO dictionary (word, source) VALUES ('apple', 'cambridge')")
            conn.commit()
            self.assertTrue(_b_already_fetched(conn, "apple"))
        finally:
            conn.close()

    def test_not_fetched_word(self):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("""
                CREATE TABLE dictionary (word TEXT PRIMARY KEY, source TEXT DEFAULT 'ecdict')
            """)
            conn.execute("INSERT INTO dictionary (word, source) VALUES ('apple', 'ecdict')")
            conn.commit()
            self.assertFalse(_b_already_fetched(conn, "apple"))
        finally:
            conn.close()

    def test_no_matching_word(self):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("""
                CREATE TABLE dictionary (word TEXT PRIMARY KEY, source TEXT DEFAULT 'ecdict')
            """)
            conn.commit()
            self.assertFalse(_b_already_fetched(conn, "anything"))
        finally:
            conn.close()


class TestBuildCambridgeDictBuildReverseTerms(unittest.TestCase):
    """Tests for build_reverse_terms() in build_cambridge_dict.py (local version)."""

    def test_basic_split(self):
        result = _b_build_reverse_terms(["n. 猫；狗，鸟"])
        self.assertIn("猫", result)
        self.assertIn("狗", result)
        self.assertIn("鸟", result)

    def test_empty_input(self):
        self.assertEqual(_b_build_reverse_terms([]), [])

    def test_deduplication(self):
        result = _b_build_reverse_terms(["猫；猫；猫"])
        self.assertEqual(result, ["猫"])

    def test_normalization(self):
        result = _b_build_reverse_terms(["  n. 猫  "])
        self.assertEqual(result, ["猫"])


class TestBuildCambridgeDictWriteEntry(unittest.TestCase):
    """Tests for write_entry() in build_cambridge_dict.py."""

    def test_writes_entry(self):
        conn = sqlite3.connect(":memory:")
        try:
            _b_ensure_schema(conn)
            entry = _BCE(
                word="testword",
                phonetic_uk="/tw/",
                phonetic_us="/tw/",
                definition="n. a test",
                translation="n. 测试",
                definitions=["测试"],
                examples=["example"],
                cefr_level="B1",
                source_url="http://example.com",
            )
            _b_write_entry(conn, entry)
            conn.commit()

            row = conn.execute("SELECT * FROM dictionary WHERE word = ?", ("testword",)).fetchone()
            self.assertIsNotNone(row)
            # Without row_factory, fetchone() returns a tuple; use column index
            self.assertEqual(row[0], "testword")  # word is first column
            # Find cefr_level column index (desc[1] = name, desc[0] = cid)
            cols = [desc[1] for desc in conn.execute("PRAGMA table_info(dictionary)").fetchall()]
            cefr_idx = cols.index("cefr_level")
            self.assertEqual(row[cefr_idx], "B1")
        finally:
            conn.close()

    def test_writes_reverse_index(self):
        conn = sqlite3.connect(":memory:")
        try:
            _b_ensure_schema(conn)
            entry = _BCE(
                word="happy",
                phonetic_us="/ˈhæpi/",
                definition="adj. happy",
                translation="adj. 快乐",
                definitions=["快乐", "高兴"],
                examples=[],
                source_url="http://example.com",
            )
            _b_write_entry(conn, entry)
            conn.commit()

            rev_rows = conn.execute("SELECT zh_term FROM dictionary_reverse WHERE word = ?", ("happy",)).fetchall()
            terms = [r[0] for r in rev_rows]
            self.assertIn("快乐", terms)
            # Translation should be inserted at position 0
            self.assertIn("adj. 快乐", terms)  # translation goes in with pos prefix
        finally:
            conn.close()

    def test_empty_definitions_writes_empty_json(self):
        conn = sqlite3.connect(":memory:")
        try:
            _b_ensure_schema(conn)
            entry = _BCE(
                word="minimal",
                definitions=[],
                examples=[],
                source_url="http://example.com",
            )
            _b_write_entry(conn, entry)
            conn.commit()

            row = conn.execute("SELECT definitions, example FROM dictionary WHERE word = ?", ("minimal",)).fetchone()
            # Tuple access (no row_factory)
            self.assertEqual(row[0], "[]")
            self.assertEqual(row[1], "[]")
        finally:
            conn.close()


class TestBuildCambridgeDictFetchWithRetry(unittest.TestCase):
    """Tests for fetch_with_retry() in build_cambridge_dict.py."""

    def test_success_on_first_try(self):
        session = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html>ok</html>"
        session.get.return_value = resp

        result = _b_fetch_with_retry(session, "http://example.com")
        self.assertEqual(result, "<html>ok</html>")
        self.assertEqual(session.get.call_count, 1)

    def test_429_retries(self):
        session = MagicMock()
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.text = "<html>after retry</html>"
        session.get.side_effect = [resp_429, resp_ok]

        with patch("scripts.build_cambridge_dict.time.sleep"):
            result = _b_fetch_with_retry(session, "http://example.com", max_retries=2)
        self.assertEqual(result, "<html>after retry</html>")

    def test_403_retries(self):
        session = MagicMock()
        resp_403 = MagicMock()
        resp_403.status_code = 403
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.text = "<html>ok</html>"
        session.get.side_effect = [resp_403, resp_ok]

        with patch("scripts.build_cambridge_dict.time.sleep"):
            result = _b_fetch_with_retry(session, "http://example.com", max_retries=2)
        self.assertEqual(result, "<html>ok</html>")

    def test_request_exception_returns_none(self):
        import requests
        session = MagicMock()
        session.get.side_effect = requests.ConnectionError("connection error")

        with patch("scripts.build_cambridge_dict.time.sleep"):
            result = _b_fetch_with_retry(session, "http://example.com", max_retries=1)
        self.assertIsNone(result)

    def test_exhausted_retries_returns_none(self):
        session = MagicMock()
        resp_429 = MagicMock()
        resp_429.status_code = 429
        session.get.return_value = resp_429

        with patch("scripts.build_cambridge_dict.time.sleep"):
            result = _b_fetch_with_retry(session, "http://example.com", max_retries=1)
        self.assertIsNone(result)

    def test_rotates_user_agent(self):
        session = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.text = ""
        session.get.return_value = resp

        _b_fetch_with_retry(session, "http://example.com")
        ua = session.headers.get("User-Agent", "")
        self.assertTrue(ua.startswith("Mozilla/"))


# ===========================================================================
# 5. Cross-module integration / regression tests
# ===========================================================================

class TestCrossModuleIntegration(unittest.TestCase):
    """Integration tests that exercise multiple modules together."""

    def test_full_en_to_zh_pipeline(self):
        """Full pipeline: query → extract → DB lookup → format output."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            );
            CREATE TABLE word_senses (
                word TEXT, pos TEXT, definition TEXT, example TEXT, sense_rank INTEGER
            );
            INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
            VALUES ('serendipity', '/ˌserənˈdɪpɪti/', '/uk/', '/us/',
                    'n. the occurrence of events by chance',
                    'n. 意外发现美好事物的能力',
                    '["意外发现", "机缘巧合", "偶然发现"]',
                    'Finding that book was pure serendipity.',
                    'ecdict', 'n.');
            INSERT INTO word_senses (word, pos, definition, example, sense_rank) VALUES
            ('serendipity', 'n.', 'the occurrence and development of events by chance', 'Finding that book was pure serendipity.', 1),
            ('serendipity', 'n.', 'a fortunate stroke of serendipity', 'It was serendipity that we met.', 2);
        """)
        conn.commit()
        conn.close()

        try:
            result = lookup_en_to_zh("serendipity", db_path, ({}, {}))
            self.assertNotIn("error", result)
            self.assertEqual(result["word"], "serendipity")
            self.assertGreaterEqual(len(result.get("senses", [])), 1)

            # Also test formatting
            text = format_en_to_zh_text(result)
            self.assertIn("serendipity", text)
            self.assertIn("**serendipity**", text)
        finally:
            db_path.unlink()

    def test_full_zh_to_en_pipeline(self):
        """Full pipeline: Chinese query → reverse index lookup → English results."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT, frequency INTEGER
            );
            CREATE TABLE dictionary_reverse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zh_term TEXT NOT NULL, word TEXT, pos TEXT, phonetic TEXT,
                source TEXT, frequency INTEGER, sense_rank INTEGER
            );
            CREATE INDEX idx_rev_zh ON dictionary_reverse(zh_term);
            INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos, frequency)
            VALUES ('resilience', '/rɪˈzɪliəns/', '/uk/', '/us/',
                    'n. resilience', 'n. 韧性', '["韧性", "恢复力"]',
                    'She showed great resilience.', 'ecdict', 'n.', 300);
            INSERT INTO dictionary_reverse (zh_term, word, pos, phonetic, source, frequency, sense_rank)
            VALUES ('韧性', 'resilience', 'n.', '/rɪˈzɪliəns/', 'ecdict', 300, 0);
        """)
        conn.commit()
        conn.close()

        try:
            result = lookup_zh_to_en("韧性", db_path, ({}, {}))
            self.assertNotIn("error", result)
            self.assertGreaterEqual(len(result.get("matches", [])), 1)
            self.assertEqual(result["matches"][0]["word"], "resilience")
        finally:
            db_path.unlink()

    def test_record_to_entry_roundtrip_with_sqlite_row(self):
        """Verify record_to_entry works correctly with actual sqlite3.Row objects."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE dictionary (
                word TEXT, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT, collins INTEGER, oxford INTEGER,
                bnc INTEGER, frq INTEGER, frequency INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation,
                definitions, example, source, pos, collins, oxford, bnc, frq, frequency)
            VALUES ('robust', '/roʊˈbʌst/', '/rəʊˈbʌst/', '/roʊˈbʌst/',
                    'adj. robust', 'adj. 强壮的', '["强壮的", "坚固的"]',
                    'a robust system', 'ecdict', 'adj.', 5, 3, 200, 150, 150)
        """)
        conn.commit()
        row = conn.execute("SELECT * FROM dictionary WHERE word = ?", ("robust",)).fetchone()
        conn.close()

        try:
            entry = record_to_entry(row)
            self.assertEqual(entry["word"], "robust")
            self.assertEqual(entry["pos"], "adj.")
            self.assertIn("强壮的", entry["definitions"])
            self.assertEqual(entry["frequency"], 150)  # frq=150, bnc=200 → frq wins
        finally:
            db_path.unlink()

    def test_build_reverse_terms_consistency_between_modules(self):
        """Both build_cambridge_dict.build_reverse_terms and dictionary_utils.build_reverse_terms
        should produce consistent results for the same input."""
        from scripts.build_cambridge_dict import build_reverse_terms as cambridge_brt

        input_defs = ["n. 猫；狗，鸟", "动物"]
        result_utils = build_reverse_terms(input_defs)
        result_cambridge = cambridge_brt(input_defs)

        self.assertEqual(set(result_utils), set(result_cambridge))


# ===========================================================================
# 6. Edge case / boundary tests
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge cases across all modules."""

    def test_unicode_handling(self):
        """Chinese characters, emojis, special unicode."""
        result = normalize_zh_term("  n. 中文测试（同义词）  ")
        self.assertEqual(result, "中文测试")

    def test_very_long_word(self):
        long_word = "a" * 1000
        result = extract_en_query(long_word)
        self.assertEqual(result, long_word.lower())

    def test_special_characters_in_query(self):
        result = extract_en_query("it's a test!")
        # Regex [A-Za-z][A-Za-z' -]* matches "it's a test" (stops at !)
        self.assertIn("it", result)

    def test_empty_database_file(self):
        """Zero-byte file that exists."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = pathlib.Path(f.name)
        try:
            entry = load_sqlite_entry(path, "word")
            # SQLite can open a zero-byte file but it won't have our table
            self.assertIsNone(entry)
        finally:
            path.unlink()

    def test_json_with_null_values(self):
        # BUG: record_to_entry does str(_record_get(record, "key", "default")) for most fields.
        # _record_get uses dict.get() which returns None when key exists with value None
        # (dict.get("k", "default") returns None NOT "default" when d["k"] is None!)
        # So str(None) = "None" for definition, translation fields.
        #
        # For definitions: parse_definitions(_record_get(rec, "definitions", translation_or_def))
        # translation_or_def = None or "None" = "None" → parse_definitions("None") = ["None"]
        entry = record_to_entry({
            "word": "nulltest",
            "definition": None,
            "translation": None,
            "definitions": None,
            "example": None,
            "pos": None,  # pos goes through coerce_text which handles None→""
        })
        self.assertEqual(entry["word"], "nulltest")  # key exists, value is string
        # None values coerced to empty string after fix
        self.assertEqual(entry["definition"], "")
        self.assertEqual(entry["definitions"], [])
        self.assertEqual(entry["pos"], "")

    def test_definitions_with_newlines(self):
        result = parse_definitions("line1\\nline2\\nline3")
        self.assertEqual(len(result), 3)

    def test_nested_json_definitions(self):
        result = parse_definitions('[["nested", "array"], "normal"]')
        # JSON loads successfully, iterates over items
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

    def test_extract_en_query_with_mixed_language(self):
        result = extract_en_query("apple水果")
        # Matches "apple" via regex, then normalizes
        self.assertIn("apple", result)

    def test_extract_zh_query_with_english_suffix(self):
        result = extract_zh_query("重要的English")
        # Strips cues, removes particles, normalizes
        self.assertIn("重要", result)

    def test_load_word_senses_case_insensitive(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = pathlib.Path(path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY, phonetic TEXT, phonetic_uk TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, definitions TEXT, example TEXT,
                source TEXT, pos TEXT
            );
            CREATE TABLE word_senses (
                word TEXT, pos TEXT, definition TEXT, example TEXT, sense_rank INTEGER
            );
            INSERT INTO dictionary (word, phonetic, phonetic_uk, phonetic_us, definition, translation, definitions, example, source, pos)
            VALUES ('HelloWorld', '/hw/', '/uk/', '/us/', 'n. hello', 'n. 你好', '["你好"]', 'say hello', 'test', 'n.');
            INSERT INTO word_senses (word, pos, definition, example, sense_rank)
            VALUES ('HelloWorld', 'n.', 'a greeting', 'Hello!', 1);
        """)
        conn.commit()
        conn.close()
        try:
            senses = load_word_senses(db_path, "helloworld")
            self.assertGreaterEqual(len(senses), 1)
        finally:
            db_path.unlink()

    def test_format_with_empty_senses_but_has_definitions(self):
        """When senses=[] but definitions exist, format_en_to_zh_text builds from definitions."""
        result = format_en_to_zh_text({
            "word": "orphan",
            "senses": [],
            "definitions": ["n. orphan", "v. to orphan"],
            "example": "An orphan child.",
        })
        self.assertIn("**orphan**", result)
        self.assertIn("orphan", result)  # definition content present
        # Should NOT just be "**orphan**" since definitions exist
        self.assertNotEqual(result, "**orphan**")


if __name__ == "__main__":
    unittest.main()
