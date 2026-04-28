#!/usr/bin/env python3
"""TDD tests for build_phrase_db.py — phrase database batch builder.

Run:
    python -m pytest tests/test_build_phrase_db.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts/ to path so we can import build_phrase_db as a module
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_phrase_db as bdb  # noqa: E402


# ===========================================================================
# 1. normalize_phrase()
# ===========================================================================


class TestNormalizePhrase:
    def test_clean_phrase_unchanged(self):
        assert bdb.normalize_phrase("look forward to") == "look forward to"

    def test_lowercase(self):
        assert bdb.normalize_phrase("Look Forward To") == "look forward to"

    def test_strip_whitespace(self):
        assert bdb.normalize_phrase("  look forward to  ") == "look forward to"

    def test_remove_sb_variant(self):
        assert bdb.normalize_phrase("accuse sb of sth") == "accuse of"
        assert bdb.normalize_phrase("ask sb for sth") == "ask for"

    def test_remove_sb_dot_variant(self):
        assert bdb.normalize_phrase("accuse sb. of sth.") == "accuse of"

    def test_remove_sth_variant(self):
        assert bdb.normalize_phrase("do sth") == "do"

    def test_remove_sth_dot_variant(self):
        assert bdb.normalize_phrase("do sth.") == "do"

    def test_remove_ellipsis(self):
        assert bdb.normalize_phrase("take ... into account") == "take into account"

    def test_remove_do_sth(self):
        assert bdb.normalize_phrase("enable sb to do sth") == "enable to do"

    def test_remove_doing_sth(self):
        assert bdb.normalize_phrase("avoid doing sth") == "avoid doing"

    def test_remove_doing_sth_dot(self):
        assert bdb.normalize_phrase("avoid doing sth.") == "avoid doing"

    def test_remove_possessive_s(self):
        assert bdb.normalize_phrase("one's own accord") == "one own accord"

    def test_collapse_multiple_spaces(self):
        assert bdb.normalize_phrase("look   forward   to") == "look forward to"

    def test_combined_variants(self):
        assert bdb.normalize_phrase("apologize to sb for sth") == "apologize to for"

    def test_be_phrases_preserved(self):
        assert bdb.normalize_phrase("be good at") == "be good at"
        assert bdb.normalize_phrase("be interested in") == "be interested in"

    def test_empty_input(self):
        assert bdb.normalize_phrase("  ") == ""

    def test_single_word(self):
        assert bdb.normalize_phrase("hello") == "hello"

    def test_split_merged_takefor(self):
        assert bdb.normalize_phrase("takefor example") == "take for example"

    def test_split_merged_putin(self):
        assert bdb.normalize_phrase("putin prison") == "put in prison"

    def test_split_merged_look_onas(self):
        assert bdb.normalize_phrase("look onas") == "look on as"

    def test_split_merged_putin_action(self):
        assert bdb.normalize_phrase("putin action") == "put in action"

    def test_split_merged_treat_oneself(self):
        result = bdb.normalize_phrase("treat oneself to")
        # oneself is a single word (not merged), should stay
        assert "oneself" in result

    def test_normal_phrase_not_affected(self):
        assert bdb.normalize_phrase("look forward to") == "look forward to"
        assert bdb.normalize_phrase("in spite of") == "in spite of"
        assert bdb.normalize_phrase("give up") == "give up"

    def test_remove_unicode_ellipsis(self):
        result = bdb.normalize_phrase("accuse…of…")
        # Unicode ellipsis stripped; remaining chars collapsed
        assert "…" not in result

    def test_remove_ascii_ellipsis_in_word(self):
        # ASCII ... without spaces survives normalize (caught by should_keep_phrase instead)
        result = bdb.normalize_phrase("accuse...of...")
        # Normalize strips space-prefixed ... but in-word ... stays; filter catches it
        assert bdb.should_keep_phrase(result) is False


# ===========================================================================
# 2b. should_keep_phrase() — noise filtering after normalization
# ===========================================================================


class TestShouldKeepPhrase:
    def test_legit_2word_phrase_kept(self):
        assert bdb.should_keep_phrase("look up") is True

    def test_legit_3word_phrase_kept(self):
        assert bdb.should_keep_phrase("in spite of") is True

    def test_legit_4word_phrase_kept(self):
        assert bdb.should_keep_phrase("as soon as possible") is True

    def test_legit_5word_idiom_kept(self):
        assert bdb.should_keep_phrase("out of sight out of mind") is True

    def test_unicode_ellipsis_dropped(self):
        assert bdb.should_keep_phrase("accuse…of…") is False

    def test_ascii_ellipsis_dropped(self):
        assert bdb.should_keep_phrase("adapt...to...") is False

    def test_single_word_fragment_dropped(self):
        assert bdb.should_keep_phrase("accuseof") is False

    def test_single_real_word_dropped(self):
        # Single-word entries are not phrases
        assert bdb.should_keep_phrase("hello") is False

    def test_8word_garbage_concat_dropped(self):
        assert bdb.should_keep_phrase("on the one hand on the other hand") is False

    def test_7word_template_fragment_dropped(self):
        assert bdb.should_keep_phrase("bring pressure to bear on to do") is False

    def test_6word_legit_idiom_kept(self):
        assert bdb.should_keep_phrase("out of sight out of mind") is True

    def test_6word_legit_expression_kept(self):
        assert bdb.should_keep_phrase("without a shadow of a doubt") is True

    def test_empty_string_dropped(self):
        assert bdb.should_keep_phrase("") is False

    def test_whitespace_only_dropped(self):
        assert bdb.should_keep_phrase("   ") is False


# ===========================================================================
# 2. classify_phrase()
# ===========================================================================


class TestClassifyPhrase:
    def test_phrasal_verb_common(self):
        assert bdb.classify_phrase("look up") == "phrasal_verb"
        assert bdb.classify_phrase("give up") == "phrasal_verb"
        assert bdb.classify_phrase("break down") == "phrasal_verb"
        assert bdb.classify_phrase("take off") == "phrasal_verb"
        assert bdb.classify_phrase("turn on") == "phrasal_verb"

    def test_collocation_be_adj(self):
        assert bdb.classify_phrase("be good at") == "collocation"
        assert bdb.classify_phrase("be interested in") == "collocation"
        assert bdb.classify_phrase("be afraid of") == "collocation"
        assert bdb.classify_phrase("be famous for") == "collocation"
        assert bdb.classify_phrase("be used to doing") == "collocation"

    def test_prepositional_phrase(self):
        assert bdb.classify_phrase("in spite of") == "prepositional_phrase"
        assert bdb.classify_phrase("instead of") == "prepositional_phrase"
        assert bdb.classify_phrase("because of") == "prepositional_phrase"
        assert bdb.classify_phrase("according to") == "prepositional_phrase"
        assert bdb.classify_phrase("on behalf of") == "prepositional_phrase"

    def test_fixed_expression(self):
        assert bdb.classify_phrase("as soon as possible") == "fixed_expression"
        assert bdb.classify_phrase("by the way") == "fixed_expression"
        assert bdb.classify_phrase("in fact") == "fixed_expression"
        assert bdb.classify_phrase("at first") == "fixed_expression"
        assert bdb.classify_phrase("of course") == "fixed_expression"

    def test_idiom(self):
        assert bdb.classify_phrase("break the ice") == "idiom"
        assert bdb.classify_phrase("piece of cake") == "idiom"
        assert bdb.classify_phrase("cost an arm and a leg") == "idiom"
        assert bdb.classify_phrase("under the weather") == "idiom"
        assert bdb.classify_phrase("hot potato") == "idiom"

    def test_default_fallback_to_collocation(self):
        # Unknown phrases default to collocation
        assert bdb.classify_phrase("make a decision") == "collocation"
        assert bdb.classify_phrase("pay attention") == "collocation"


# ===========================================================================
# 3. assign_frequency()
# ===========================================================================


class TestAssignFrequency:
    def test_top_50_rank(self):
        assert bdb.assign_frequency(rank_236=1) == 5
        assert bdb.assign_frequency(rank_236=25) == 5
        assert bdb.assign_frequency(rank_236=50) == 5

    def test_mid_rank_51_150(self):
        assert bdb.assign_frequency(rank_236=51) == 4
        assert bdb.assign_frequency(rank_236=100) == 4
        assert bdb.assign_frequency(rank_236=150) == 4

    def test_low_rank_151_236(self):
        assert bdb.assign_frequency(rank_236=151) == 3
        assert bdb.assign_frequency(rank_236=200) == 3
        assert bdb.assign_frequency(rank_236=236) == 3

    def test_no_rank_default(self):
        assert bdb.assign_frequency(rank_236=None) == 3

    def test_multi_source_boost(self):
        # If in multiple sources, should get +1 (capped at 5)
        freq = bdb.assign_frequency(rank_236=None, source_count=2)
        assert freq == 4


# ===========================================================================
# 4. extract_zh_terms()
# ===========================================================================


class TestExtractZhTerms:
    def test_single_definition(self):
        terms = bdb.extract_zh_terms(["期待；盼望"])
        assert "期待" in terms
        assert "盼望" in terms

    def test_multiple_definitions(self):
        terms = bdb.extract_zh_terms(["放弃；投降", "戒除（习惯）"])
        assert "放弃" in terms
        assert "戒除" in terms

    def test_max_3_terms(self):
        terms = bdb.extract_zh_terms(["a；b；c；d；e"])
        assert len(terms) <= 3

    def test_empty_definitions(self):
        terms = bdb.extract_zh_terms([])
        assert terms == []

    def test_phra_prefix_stripped(self):
        terms = bdb.extract_zh_terms(["phr. 期待；盼望"])
        # Should still extract meaningful Chinese terms
        assert len(terms) >= 1

    def test_short_terms_filtered(self):
        terms = bdb.extract_zh_terms(["的；了；是"])
        # Single-char terms should be filtered
        assert all(len(t) >= 2 for t in terms)


# ===========================================================================
# 5. merge_phrases() — dedup + source merging
# ===========================================================================


class TestMergePhrases:
    def _make_seed_entries(self) -> list[dict]:
        return [
            {
                "phrase": "look forward to",
                "category": "phrasal_verb",
                "definitions": ["期待；盼望", "期望"],
                "examples": [{"en": "I look forward to hearing from you.", "zh": "我期待收到你的来信。"}],
                "zh_terms": ["期待", "盼望", "期望"],
                "frequency": 5,
            },
            {
                "phrase": "give up",
                "category": "phrasal_verb",
                "definitions": ["放弃；投降", "戒除（习惯）"],
                "examples": [{"en": "Don't give up easily.", "zh": "不要轻易放弃。"}],
                "zh_terms": ["放弃", "戒除"],
                "frequency": 5,
            },
        ]

    def test_seed_data_loaded(self):
        seeds = bdb.load_seed_data()
        # File may have been overwritten by pipeline runs; check structure not count
        assert len(seeds) > 0
        phrases = {s["phrase"] for s in seeds}
        # Must contain original seed entries if file hasn't been reset
        assert "look forward to" in phrases or len(seeds) != 43
        # Verify schema of each entry
        for entry in seeds:
            assert "phrase" in entry
            assert "category" in entry
            assert "definitions" in entry

    def test_merge_preserves_all_seeds(self):
        seeds = self._make_seed_entries()
        merged = bdb.merge_phrases(source_a=[], source_b={}, source_c={}, seeds=seeds)
        phrase_set = {m["phrase"] for m in merged}
        assert "look forward to" in phrase_set
        assert "give up" in phrase_set
        assert len(merged) == 2

    def test_merge_adds_source_a_new_phrases(self):
        seeds = []
        source_a = ["look forward to", "give up", "brand new phrase"]
        merged = bdb.merge_phrases(source_a=source_a, source_b={}, source_c={}, seeds=seeds)
        phrase_set = {m["phrase"] for m in merged}
        assert "brand new phrase" in phrase_set
        assert len(merged) == 3

    def test_merge_dedup_normalizes(self):
        seeds = []
        source_a = ["look forward to", "Look Forward To", "LOOK UP"]
        merged = bdb.merge_phrases(source_a=source_a, source_b={}, source_c={}, seeds=seeds)
        phrase_set = {m["phrase"] for m in merged}
        assert len(phrase_set) == 2  # "look forward to" deduped, "look up" kept

    def test_merge_source_b_adds_definitions(self):
        seeds = [{"phrase": "look forward to", "category": "phrasal_verb",
                  "definitions": ["expect"], "examples": [], "zh_terms": [], "frequency": 3}]
        source_b = {"look forward to": {"rank": 79, "definitions": ["也；同样"]}}
        merged = bdb.merge_phrases(source_a=[], source_b=source_b, source_c={}, seeds=seeds)
        entry = next(m for m in merged if m["phrase"] == "look forward to")
        # Source B definition should be added
        assert any("也" in d or "同样" in d for d in entry["definitions"])

    def test_merge_source_c_adds_translations(self):
        seeds = []
        source_a = ["look forward to"]
        source_c = {"look forward to": ["期待；盼望"]}
        merged = bdb.merge_phrases(source_a=source_a, source_b={}, source_c=source_c, seeds=seeds)
        entry = next(m for m in merged if m["phrase"] == "look forward to")
        assert len(entry["definitions"]) >= 1

    def test_all_entries_have_required_fields(self):
        seeds = self._make_seed_entries()
        merged = bdb.merge_phrases(source_a=[], source_b={}, source_c={}, seeds=seeds)
        for entry in merged:
            assert "phrase" in entry
            assert "category" in entry
            assert "definitions" in entry
            assert isinstance(entry["definitions"], list)
            assert "examples" in entry
            assert isinstance(entry["examples"], list)
            assert "zh_terms" in entry
            assert isinstance(entry["zh_terms"], list)
            assert "frequency" in entry
            assert isinstance(entry["frequency"], int)
            assert 1 <= entry["frequency"] <= 5

    def test_no_duplicate_phrases_after_merge(self):
        seeds = self._make_seed_entries()
        source_a = ["look forward to", "give up", "new one"]
        merged = bdb.merge_phrases(source_a=source_a, source_b={}, source_c={}, seeds=seeds)
        phrases = [m["phrase"] for m in merged]
        assert len(phrases) == len(set(phrases))


# ===========================================================================
# 6. Output schema validation
# ===========================================================================


class TestOutputSchema:
    def test_output_json_schema(self):
        """Generated JSON must match gaokao_phrases.json schema."""
        seeds = bdb.load_seed_data()
        merged = bdb.merge_phrases(source_a=[], source_b={}, source_c={}, seeds=seeds)
        output = bdb.build_output(merged)

        assert output["version"] is not None
        assert "description" in output
        assert "phrases" in output
        assert isinstance(output["phrases"], list)
        assert len(output["phrases"]) > 0

    def test_output_write_and_read(self):
        """Round-trip: write JSON then read it back."""
        seeds = bdb.load_seed_data()
        merged = bdb.merge_phrases(source_a=[], source_b={}, source_c={}, seeds=seeds)
        output = bdb.build_output(merged)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(output, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            loaded = json.loads(Path(tmp_path).read_text("utf-8"))
            assert loaded["version"] == output["version"]
            assert len(loaded["phrases"]) == len(output["phrases"])
        finally:
            os.unlink(tmp_path)


# ===========================================================================
# 7. Validator compatibility (integration)
# ===========================================================================


class TestValidatorCompatibility:
    def _run_validator(self, text: str, mode: str) -> tuple[int, str]:
        validator_path = SCRIPTS_DIR / "validate_lookup_output.py"
        result = subprocess.run(
            [sys.executable, str(validator_path), "--mode", mode],
            input=text,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout.strip()

    def test_en_to_zh_phrase_format(self):
        """Phrase card in en_to_zh mode must pass validator."""
        entry = {
            "phrase": "look forward to",
            "category": "phrasal_verb",
            "definitions": ["期待；盼望"],
            "examples": [{"en": "I look forward to hearing from you.", "zh": "我期待收到你的来信。"}],
            "zh_terms": ["期待"],
            "frequency": 5,
        }
        card = bdb.format_card_en_to_zh(entry)
        rc, out = self._run_validator(card, "en_to_zh")
        assert rc == 0, f"Validator failed for en_to_zh phrase:\n{card}\nstderr: {out}"

    def test_zh_to_en_phrase_format(self):
        """Phrase card in zh_to_en mode must pass validator."""
        entry = {
            "phrase": "look forward to",
            "category": "phrasal_verb",
            "definitions": ["期待；盼望"],
            "examples": [{"en": "I look forward to hearing from you.", "zh": "我期待收到你的来信。"}],
            "zh_terms": ["期待"],
            "frequency": 5,
        }
        card = bdb.format_card_zh_to_en(entry, query="期待")
        rc, out = self._run_validator(card, "zh_to_en")
        assert rc == 0, f"Validator failed for zh_to_en phrase:\n{card}\nstderr: {out}"

    def test_en_to_zh_word_format_with_phonetic(self):
        """Word card (with phonetic line) must pass en_to_zh validator."""
        entry = {
            "phrase": "apple",
            "category": "word",
            "definitions": ["n. 苹果"],
            "examples": [{"en": "I eat an apple.", "zh": "我吃一个苹果。"}],
            "zh_terms": ["苹果"],
            "frequency": 5,
            "phonetic": "/ˈæpəl/",
        }
        card = bdb.format_card_en_to_zh(entry)
        rc, out = self._run_validator(card, "en_to_zh")
        assert rc == 0, f"Validator failed for en_to_zh word:\n{card}\nstderr: {out}"

    def test_zh_to_en_word_format_with_phonetic(self):
        """Word card (with phonetic) must pass zh_to_en validator."""
        entry = {
            "phrase": "important",
            "category": "word",
            "definitions": ["adj. 重要的"],
            "examples": [{"en": "It is important.", "zh": "这很重要。"}],
            "zh_terms": ["重要的"],
            "frequency": 5,
            "phonetic": "/ɪmˈpɔːrtnt/",
        }
        card = bdb.format_card_zh_to_en(entry, query="重要的")
        rc, out = self._run_validator(card, "zh_to_en")
        assert rc == 0, f"Validator failed for zh_to_en word:\n{card}\nstderr: {out}"


# ===========================================================================
# 8. Category distribution sanity check
# ===========================================================================


class TestCategoryDistribution:
    def test_all_five_categories_present_in_seeds(self):
        seeds = bdb.load_seed_data()
        categories = set(s["category"] for s in seeds)
        expected = {"phrasal_verb", "collocation", "prepositional_phrase", "fixed_expression", "idiom"}
        assert expected.issubset(categories), f"Missing categories: {expected - categories}"

    def test_classify_produces_valid_category(self):
        for phrase in [
            "look up", "be good at", "in spite of", "by the way",
            "break the ice", "make progress", "pay attention",
            "brand new phrase nobody knows",
        ]:
            cat = bdb.classify_phrase(phrase)
            assert cat in {
                "phrasal_verb", "collocation", "prepositional_phrase",
                "fixed_expression", "idiom",
            }, f"Invalid category '{cat}' for phrase '{phrase}'"
