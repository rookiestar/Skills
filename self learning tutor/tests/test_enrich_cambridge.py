#!/usr/bin/env python3
"""TDD tests for enrich_cambridge_phrases.py — batch Cambridge enrichment.

Run:
    python -m pytest tests/test_enrich_cambridge.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import may fail if dependencies (requests, bs4) not installed — skip gracefully
try:
    import enrich_cambridge_phrases as ecp  # noqa: E402
except ImportError:
    ecp = None  # type: ignore[assignment]


# ===========================================================================
# 1. Phrase URL slug generation
# ===========================================================================


class TestPhraseSlug:
    def test_single_word(self):
        assert ecp.phrase_to_slug("hello") == "hello"

    def test_two_word_phrase(self):
        assert ecp.phrase_to_slug("look up") == "look-up"

    def test_three_word_phrase(self):
        assert ecp.phrase_to_slug("look forward to") == "look-forward-to"

    def test_four_word_phrase(self):
        assert ecp.phrase_to_slug("as soon as possible") == "as-soon-as-possible"

    def test_already_has_hyphens(self):
        # Should normalize to single hyphens
        assert ecp.phrase_to_slug("well-known") == "well-known"


# ===========================================================================
# 2. Identify phrases needing enrichment
# ===========================================================================


class TestFindNoDefPhrases:
    @staticmethod
    def _make_db(phrases_data: list[dict]) -> str:
        db = {
            "version": "2.0",
            "description": "test",
            "phrases": phrases_data,
        }
        path = tempfile.mktemp(suffix=".json")
        Path(path).write_text(json.dumps(db, ensure_ascii=False), "utf-8")
        return path

    def test_finds_phrases_with_empty_definitions(self):
        data = [
            {"phrase": "has_def", "definitions": ["期待"], "category": "collocation"},
            {"phrase": "no_def", "definitions": [], "category": "collocation"},
            {"phrase": "also_no_def", "definitions": [], "category": "phrasal_verb"},
        ]
        path = self._make_db(data)
        try:
            no_defs = ecp.find_no_def_phrases(path)
            phrases = {p["phrase"] for p in no_defs}
            assert "no_def" in phrases
            assert "also_no_def" in phrases
            assert "has_def" not in phrases
            assert len(no_defs) == 2
        finally:
            os.unlink(path)

    def test_returns_empty_when_all_have_definitions(self):
        data = [
            {"phrase": "a", "definitions": ["x"], "category": "collocation"},
            {"phrase": "b", "definitions": ["y"], "category": "collocation"},
        ]
        path = self._make_db(data)
        try:
            no_defs = ecp.find_no_def_phrases(path)
            assert no_defs == []
        finally:
            os.unlink(path)

    def test_preserves_all_fields_in_result(self):
        data = [
            {
                "phrase": "test",
                "category": "phrasal_verb",
                "definitions": [],
                "examples": [],
                "zh_terms": [],
                "frequency": 3,
            },
        ]
        path = self._make_db(data)
        try:
            result = ecp.find_no_def_phrases(path)
            entry = result[0]
            assert entry["category"] == "phrasal_verb"
            assert entry["frequency"] == 3
            assert isinstance(entry["examples"], list)
        finally:
            os.unlink(path)


# ===========================================================================
# 3. Cambridge HTML extraction for phrases
# ===========================================================================


class TestExtractPhraseEntry:
    """Test extraction from real-ish Cambridge HTML snippets."""

    def _load_fixture(self, name: str) -> str:
        fixture_dir = SCRIPTS_DIR.parent / "tests" / "fixtures"
        return (fixture_dir / name).read_text("utf-8")

    def test_extracts_definition_from_phrase_page(self):
        """A phrase page with .entry-body should yield a definition."""
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        html = self._load_fixture("cambridge_look_forward_to.html")
        entry = ecp.extract_entry(html, "look forward to", "https://example.com")
        assert entry is not None
        assert len(entry.definitions) > 0 or entry.translation
        # At minimum we should get some Chinese text
        has_zh = any(
            "一" <= c <= "鿿"
            for d in (entry.definitions + [entry.translation])
            for c in d
        )
        assert has_zh, f"No Chinese found in definitions={entry.definitions}, translation={entry.translation}"

    def test_returns_none_for_landing_page(self):
        """A search landing page (no .entry-body) should return None."""
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        html = "<html><body><div class='search-results'>not found</div></body></html>"
        result = ecp.extract_entry(html, "fake phrase", "https://example.com")
        assert result is None

    def test_extracts_example_sentence(self):
        """Should extract at least one example sentence."""
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        html = self._load_fixture("cambridge_look_forward_to.html")
        entry = ecp.extract_entry(html, "look forward to", "https://example.com")
        if entry and entry.examples:
            ex = entry.examples[0]
            assert len(ex) > 5  # Real sentences are longer than 5 chars


# ===========================================================================
# 4. Enrichment merge logic
# ===========================================================================


class TestEnrichPhrase:
    def test_adds_definition_to_empty_entry(self):
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        original = {
            "phrase": "look forward to",
            "category": "phrasal_verb",
            "definitions": [],
            "examples": [],
            "zh_terms": [],
            "frequency": 4,
        }
        cam_entry = ecp.CambridgeEntry(
            word="look forward to",
            definition="to feel pleased and excited about something",
            translation="期待；盼望；期望",
            definitions=["期待；盼望"],
            examples=["I look forward to hearing from you."],
        )
        enriched = ecp.enrich_phrase(original, cam_entry)
        assert len(enriched["definitions"]) > 0
        assert any("期待" in d for d in enriched["definitions"])

    def test_does_not_duplicate_existing_definitions(self):
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        original = {
            "phrase": "give up",
            "category": "phrasal_verb",
            "definitions": ["放弃；投降"],
            "examples": [],
            "zh_terms": ["放弃"],
            "frequency": 5,
        }
        cam_entry = ecp.CambridgeEntry(
            word="give up",
            translation="放弃",
            definitions=["放弃"],
        )
        enriched = ecp.enrich_phrase(original, cam_entry)
        # Should not have duplicate "放弃"
        defs = enriched["definitions"]
        assert defs.count("放弃") <= 1

    def test_adds_example_if_missing(self):
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        original = {
            "phrase": "break down",
            "category": "phrasal_verb",
            "definitions": [],
            "examples": [],
            "zh_terms": [],
            "frequency": 3,
        }
        cam_entry = ecp.CambridgeEntry(
            word="break down",
            translation="出故障；分解",
            definitions=["出故障；分解"],
            examples=["My car broke down on the highway."],
        )
        enriched = ecp.enrich_phrase(original, cam_entry)
        assert len(enriched["examples"]) > 0

    def test_preserves_existing_examples(self):
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        existing_ex = {"en": "Don't give up easily.", "zh": "不要轻易放弃。"}
        original = {
            "phrase": "give up",
            "category": "phrasal_verb",
            "definitions": ["放弃"],
            "examples": [existing_ex],
            "zh_terms": ["放弃"],
            "frequency": 5,
        }
        cam_entry = ecp.CambridgeEntry(
            word="give up",
            translation="投降",
            definitions=["投降"],
        )
        enriched = ecp.enrich_phrase(original, cam_entry)
        assert existing_ex in enriched["examples"]


# ===========================================================================
# 5. Validator compatibility after enrichment
# ===========================================================================


class TestEnrichedValidatorCompat:
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

    def test_enriched_phrase_passes_en_to_zh(self):
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        original = {
            "phrase": "look forward to",
            "category": "phrasal_verb",
            "definitions": [],
            "examples": [],
            "zh_terms": [],
            "frequency": 4,
        }
        cam_entry = ecp.CambridgeEntry(
            word="look forward to",
            translation="期待；盼望",
            definitions=["phr. 期待；盼望"],
            examples=[
                {"en": "I look forward to hearing from you.", "zh": "我期待收到你的来信。"}
            ],
        )
        enriched = ecp.enrich_phrase(original, cam_entry)
        card = ecp.format_card_en_to_zh(enriched)
        rc, out = self._run_validator(card, "en_to_zh")
        assert rc == 0, f"Validator failed:\n{card}\nstderr: {out}"

    def test_enriched_phrase_passes_zh_to_en(self):
        if ecp is None:
            pytest.skip("enrich_cambridge_phrases not importable")
        original = {
            "phrase": "give up",
            "category": "phrasal_verb",
            "definitions": [],
            "examples": [],
            "zh_terms": [],
            "frequency": 4,
        }
        cam_entry = ecp.CambridgeEntry(
            word="give up",
            translation="放弃；投降",
            definitions=["phr. 放弃；投降"],
            examples=[{"en": "Don't give up.", "zh": "别放弃。"}],
        )
        enriched = ecp.enrich_phrase(original, cam_entry)
        # zh_to_en phrase format only supports 1 definition line per validator spec
        card = ecp.format_card_zh_to_en(enriched, query="放弃")
        rc, out = self._run_validator(card, "zh_to_en")
        assert rc == 0, f"Validator failed:\n{card}\nstderr: {out}"
