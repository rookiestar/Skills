"""Regression tests for bolding target words and phrases in dictionary examples."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dict_lookup import _bold_word_in_text  # noqa: E402


def test_contiguous_phrase_is_bolded_as_one_span():
    text = "I'm sure at some point in the future I'll want a baby."
    result = _bold_word_in_text("in the future", text)
    assert "**in the future**" in result
    assert "**in the** future" not in result


def test_discontinuous_phrase_keeps_separate_parts():
    text = "She put her shirt on quickly."
    result = _bold_word_in_text("put on", text)
    assert "**put**" in result
    assert "**on**" in result
    assert "**put on**" not in result


def test_single_word_does_not_match_inside_longer_word():
    text = "The safeguard was removed."
    result = _bold_word_in_text("guard", text)
    assert result == text


def test_single_word_bolds_plural_tail_together():
    text = "neck /back /leg / stomach muscles"
    result = _bold_word_in_text("muscle", text)
    assert "**muscles**" in result
    assert "**muscle**s" not in result
