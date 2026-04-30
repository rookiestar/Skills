#!/usr/bin/env python3
"""Local dictionary lookup for self-learning-tutor."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dictionary_utils import (  # noqa: E402
    build_reverse_terms,
    normalize_query,
    normalize_zh_term,
    record_to_entry,
    strip_lookup_cues_en,
    strip_lookup_cues_zh,
)


def resolve_path(value: str | None, env_name: str, default: Path) -> Path:
    if value:
        return Path(value)
    env_value = os.environ.get(env_name)
    if env_value:
        return Path(env_value)
    return default


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def load_sample_indexes(sample_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if not sample_path.exists():
        return {}, {}

    raw = json.loads(sample_path.read_text(encoding="utf-8"))
    by_word: dict[str, dict[str, Any]] = {}
    by_zh: dict[str, list[dict[str, Any]]] = {}

    for item in raw:
        entry = record_to_entry(item)
        if not entry["word"]:
            continue
        by_word[entry["word"].lower()] = entry
        zh_terms = item.get("zh_terms") if isinstance(item, dict) else None
        terms = build_reverse_terms(entry["definitions"], zh_terms if isinstance(zh_terms, list) else None)
        if not terms:
            terms = entry["definitions"]
        for term in terms:
            by_zh.setdefault(normalize_zh_term(term), []).append(entry)

    return by_word, by_zh


def entry_for_output(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "word": entry["word"],
        "pos": entry["pos"],
        "phonetic": entry["phonetic"],
        "definitions": entry["definitions"],
        "example": entry["example"],
        "source": entry["source"],
    }


def extract_en_query(query: str) -> str:
    text = strip_lookup_cues_en(query)
    match = re.match(r"[A-Za-z][A-Za-z' -]*", text)
    if match:
        return normalize_query(match.group(0)).lower()
    return normalize_query(text).lower()


def extract_zh_query(query: str) -> str:
    text = strip_lookup_cues_zh(query)
    text = re.sub(r"[吗嘛呀啊呢哦吧哈！？。.？]+$", "", text).strip()
    return normalize_zh_term(text)


def load_sqlite_entry(db_path: Path, word: str) -> dict[str, Any] | None:
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "dictionary"):
            return None
        row = conn.execute(
            "SELECT * FROM dictionary WHERE lower(word) = ? OR word = ? LIMIT 1",
            (word.lower(), word),
        ).fetchone()
        if row is None:
            return None
        return record_to_entry(row)
    finally:
        conn.close()


def load_sqlite_matches(db_path: Path, query: str, limit: int = 2) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        matches: list[dict[str, Any]] = []
        if table_exists(conn, "dictionary_reverse"):
            rows = conn.execute(
                """
                SELECT zh_term, word, pos, phonetic, source, frequency, sense_rank
                FROM dictionary_reverse
                WHERE zh_term = ?
                ORDER BY CASE WHEN frequency > 0 THEN 0 ELSE 1 END, sense_rank ASC, frequency ASC, word ASC
                LIMIT ?
                """,
                (query, limit * 4),
            ).fetchall()
            if not rows:
                rows = conn.execute(
                    """
                SELECT zh_term, word, pos, phonetic, source, frequency, sense_rank
                FROM dictionary_reverse
                WHERE zh_term LIKE ? OR ? LIKE zh_term
                    ORDER BY CASE WHEN frequency > 0 THEN 0 ELSE 1 END, sense_rank ASC, frequency ASC, word ASC
                    LIMIT ?
                    """,
                    (f"%{query}%", query, limit * 4),
                ).fetchall()

            seen: set[str] = set()
            for row in rows:
                word = row["word"]
                if word in seen:
                    continue
                seen.add(word)
                entry = load_sqlite_entry(db_path, word)
                if entry is None:
                        entry = {
                            "word": word,
                            "pos": row["pos"] or "",
                            "phonetic": row["phonetic"] or "",
                            "definitions": [],
                            "example": "",
                            "source": row["source"] or "ecdict",
                        }
                matches.append(entry_for_output(entry))
                if len(matches) >= limit:
                    break
            if matches:
                return matches

        if table_exists(conn, "dictionary"):
            rows = conn.execute("SELECT word, definitions FROM dictionary LIMIT 100").fetchall()
            seen = set()
            for row in rows:
                entry = record_to_entry(row)
                if not entry["word"] or entry["word"] in seen:
                    continue
                candidates = build_reverse_terms(entry["definitions"], None)
                if any(query == candidate or query in candidate or candidate in query for candidate in candidates):
                    seen.add(entry["word"])
                    matches.append(entry_for_output(entry))
                    if len(matches) >= limit:
                        break
        return matches
    finally:
        conn.close()


def load_word_senses(db_path: Path, word: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "word_senses"):
            entry = load_sqlite_entry(db_path, word)
            if entry:
                defs = entry.get("definitions") or []
                raw_examples = entry.get("example", "")
                examples: list[str] = []
                if raw_examples:
                    try:
                        parsed = json.loads(raw_examples)
                        if isinstance(parsed, list):
                            examples = parsed
                        else:
                            examples = [str(parsed)] if str(parsed) else []
                    except (json.JSONDecodeError, TypeError):
                        examples = [raw_examples] if raw_examples else []
                return [{"word": entry["word"], "phonetic": entry.get("phonetic", ""), "definition": d, "example": examples[i] if i < len(examples) else ""} for i, d in enumerate(defs[:5]) if d]
            return []
        rows = conn.execute(
            "SELECT s.pos,s.definition,s.example,s.sense_rank,d.phonetic,d.phonetic_uk,d.phonetic_us,d.word,d.source FROM word_senses s JOIN dictionary d ON s.word=d.word WHERE lower(d.word)=? ORDER BY s.sense_rank ASC LIMIT 6",
            (word.lower(),),
        ).fetchall()
        result = []
        phonetic = ""
        for row in rows:
            if not phonetic:
                phonetic = row["phonetic_uk"] or row["phonetic_us"] or row["phonetic"] or ""
            result.append({"word": row["word"], "pos": row["pos"] or "", "phonetic": phonetic, "definition": row["definition"], "example": row["example"] or "", "source": row["source"] or ""})
        return result
    finally:
        conn.close()


def load_sample_entry(sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]], word: str) -> dict[str, Any] | None:
    by_word, _ = sample_indexes
    return by_word.get(word.lower())


def load_sample_matches(sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]], query: str, limit: int = 2) -> list[dict[str, Any]]:
    _, by_zh = sample_indexes
    matches = list(by_zh.get(query, []))
    if not matches:
        for term, entries in by_zh.items():
            if query in term or term in query:
                matches.extend(entries)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in sorted(matches, key=lambda item: (-item.get("frequency", 0), item["word"])):
        if entry["word"] in seen:
            continue
        seen.add(entry["word"])
        deduped.append(entry_for_output(entry))
        if len(deduped) >= limit:
            break
    return deduped


def append_missing_word(missing_log: Path, query: str) -> None:
    missing_log.parent.mkdir(parents=True, exist_ok=True)
    with missing_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{query}\n")


def format_en_to_zh_text(result: dict[str, Any]) -> str:
    word = result.get("word", "")
    senses = result.get("senses", [])

    if not senses and "definitions" in result:
        senses = [{"pos": result.get("pos", ""), "definition": d, "example": result.get("example", "") if i == 0 else ""} for i, d in enumerate((result.get("definitions") or [])[:3]) if d]

    if not senses:
        return f"**{word}**"

    parts = [f"**{word}**"]

    phonetic = senses[0].get("phonetic", "") or ""
    if phonetic:
        parts.append(f"\n🔤 {phonetic}\n")

    for i, s in enumerate(senses[:5]):
        definition = s.get("definition") or ""
        example = s.get("example") or ""

        num = f"{i + 1}. "
        parts.append(f"{num}{definition}")

        if example:
            parts.append(f"\t💬 {example}")

        if i < len(senses[:5]) - 1:
            parts.append("")

    return "\n".join(parts)


def _extract_pos_from_raw_defs(db_path: Path, word: str) -> str:
    """Recover POS prefix from raw definitions JSON (before parse_definitions strips it)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT definitions FROM dictionary WHERE lower(word) = ? LIMIT 1",
            (word.lower(),),
        ).fetchone()
        if not row:
            return ""
        raw_text = row["definitions"] or ""
        try:
            raw_defs = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
        except (json.JSONDecodeError, TypeError):
            return ""
        if not isinstance(raw_defs, list) or not raw_defs:
            return ""
        m = re.match(r"^([a-z]{1,5}\.)\s*", str(raw_defs[0]))
        return m.group(1) if m else ""
    finally:
        conn.close()


def lookup_en_to_zh(query: str, db_path: Path, sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    word = extract_en_query(query)
    entry = load_sqlite_entry(db_path, word)
    if entry is None:
        entry = load_sample_entry(sample_indexes, word)
    if entry is None:
        append_missing_word(db_path.parent / "missing_words.log", word)
        return {"error": "not_found", "mode": "en_to_zh", "query": word}
    defs = entry.get("definitions") or []
    entry_pos = entry.get("pos", "") or _extract_pos_from_raw_defs(db_path, word)
    raw_examples = entry.get("example", "")
    examples: list[str] = []
    if raw_examples:
        try:
            parsed = json.loads(raw_examples)
            if isinstance(parsed, list):
                examples = parsed
            else:
                examples = [str(parsed)] if str(parsed) else []
        except (json.JSONDecodeError, TypeError):
            examples = [raw_examples] if raw_examples else []
    senses = [{"word": entry["word"], "phonetic": entry.get("phonetic", ""), "pos": entry_pos, "definition": d, "example": examples[i] if i < len(examples) else ""} for i, d in enumerate(defs[:5]) if d]
    return {"word": word, "senses": senses}


def lookup_zh_to_en(query: str, db_path: Path, sample_indexes: tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    phrase = extract_zh_query(query)
    matches = load_sqlite_matches(db_path, phrase)
    if not matches:
        matches = load_sample_matches(sample_indexes, phrase)
    if not matches:
        append_missing_word(db_path.parent / "missing_words.log", phrase)
        return {"error": "not_found", "mode": "zh_to_en", "query": phrase}
    return {"query": phrase, "matches": matches}


def _clean_def_text(text: str) -> str:
    """Strip noise prefixes from definition text (quotes, embedded POS)."""
    text = text.strip().strip('"').strip()
    text = re.sub(r'^[a-z]{1,5}\.\s*', '', text)
    return text


def _bold_word_in_text(word: str, text: str) -> str:
    """Bold target word (or each part of a phrase) within text.

    Single word: full-word replace (allows 'Guards' → 'guard').
    Phrase: position-based matching per sentence. Within each sentence,
    greedy chains parts left-to-right with non-overlapping constraint.
    Allows small word gaps for phrasal verbs ('put her shirt on'),
    but applies contiguous-priority filter **per sentence** so that
    'puts ... on' and 'puts on' in different sentences both get bolded.
    Supports verb conjugation: 'be good at' matches 'is/are/was good at',
    'put on' matches 'puts/putting/put ... on'.
    """
    def _repl(m):
        return f"**{m.group(0)}**"

    parts = word.split()
    if len(parts) == 1:
        lower = word.lower()
        if len(lower) > 2 and not lower.endswith("s"):
            pat = rf"(?<![A-Za-z]){re.escape(word)}(?=s\b|\b)"
        else:
            pat = rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])"
        return re.sub(pat, _repl, text, flags=re.IGNORECASE)

    _PARTICLES = {
        "about", "after", "along", "around", "away", "back", "by", "down",
        "for", "in", "into", "off", "on", "out", "over", "through", "to",
        "up", "with",
    }
    _NON_VERB_FIRST_PARTS = {
        "able", "afraid", "aware", "bad", "busy", "careful", "certain",
        "different", "due", "familiar", "famous", "fond", "full", "good",
        "great", "happy", "interested", "keen", "late", "likely", "poor",
        "proud", "ready", "responsible", "similar", "sorry", "sure",
        "used", "worth",
    }
    max_word_gap = 4 if len(parts) == 2 and parts[-1].lower() in _PARTICLES else 2

    _AUX_CONJ: dict[str, str] = {
        "be": "(?:am|is|are|was|were|be|been|being)",
        "have": "(?:have|has|had|having)",
        "do": "(?:do|does|did|doing)",
    }
    _IRREGULAR_VERBS: dict[str, tuple[str, ...]] = {
        "be": ("am", "is", "are", "was", "were", "be", "been", "being"),
        "become": ("become", "becomes", "became", "becoming"),
        "begin": ("begin", "begins", "began", "begun", "beginning"),
        "break": ("break", "breaks", "broke", "broken", "breaking"),
        "bring": ("bring", "brings", "brought", "bringing"),
        "buy": ("buy", "buys", "bought", "buying"),
        "catch": ("catch", "catches", "caught", "catching"),
        "come": ("come", "comes", "came", "coming"),
        "do": ("do", "does", "did", "done", "doing"),
        "fall": ("fall", "falls", "fell", "fallen", "falling"),
        "feel": ("feel", "feels", "felt", "feeling"),
        "find": ("find", "finds", "found", "finding"),
        "get": ("get", "gets", "got", "gotten", "getting"),
        "give": ("give", "gives", "gave", "given", "giving"),
        "go": ("go", "goes", "went", "gone", "going"),
        "have": ("have", "has", "had", "having"),
        "hear": ("hear", "hears", "heard", "hearing"),
        "hold": ("hold", "holds", "held", "holding"),
        "keep": ("keep", "keeps", "kept", "keeping"),
        "know": ("know", "knows", "knew", "known", "knowing"),
        "leave": ("leave", "leaves", "left", "leaving"),
        "lose": ("lose", "loses", "lost", "losing"),
        "make": ("make", "makes", "made", "making"),
        "meet": ("meet", "meets", "met", "meeting"),
        "pay": ("pay", "pays", "paid", "paying"),
        "put": ("put", "puts", "putting"),
        "read": ("read", "reads", "reading"),
        "run": ("run", "runs", "ran", "running"),
        "say": ("say", "says", "said", "saying"),
        "see": ("see", "sees", "saw", "seen", "seeing"),
        "send": ("send", "sends", "sent", "sending"),
        "set": ("set", "sets", "setting"),
        "show": ("show", "shows", "showed", "shown", "showing"),
        "sit": ("sit", "sits", "sat", "sitting"),
        "speak": ("speak", "speaks", "spoke", "spoken", "speaking"),
        "stand": ("stand", "stands", "stood", "standing"),
        "take": ("take", "takes", "took", "taken", "taking"),
        "tell": ("tell", "tells", "told", "telling"),
        "think": ("think", "thinks", "thought", "thinking"),
        "write": ("write", "writes", "wrote", "written", "writing"),
    }

    def _verb_forms(base: str) -> list[str]:
        lower = base.lower()
        if lower in _IRREGULAR_VERBS:
            return list(_IRREGULAR_VERBS[lower])

        forms = [lower]
        if lower.endswith(("s", "x", "z", "ch", "sh", "o")):
            forms.append(lower + "es")
        else:
            forms.append(lower + "s")

        def _cvc_double(stem: str) -> str:
            if len(stem) >= 3 and stem[-1].isalpha() and not stem[-1] in "aeiouwxy":
                if stem[-2] in "aeiou" and (len(stem) < 3 or stem[-3] not in "aeiou"):
                    return stem + stem[-1]
            return stem

        if lower.endswith("ie"):
            forms.append(lower[:-2] + "ying")
        elif lower.endswith("e") and len(lower) > 2:
            forms.append(lower[:-1] + "ing")
        else:
            forms.append(_cvc_double(lower) + "ing")
        if lower.endswith("e"):
            forms.append(lower + "d")
        else:
            forms.append(_cvc_double(lower) + "ed")
        return forms

    def _word_boundary_pattern(forms: list[str]) -> str:
        return r"(?<![A-Za-z])(?:" + "|".join(re.escape(f) for f in forms) + r")(?![A-Za-z])"

    def _pattern_for(part: str, part_index: int) -> str:
        lower = part.lower()
        if lower in _AUX_CONJ:
            return r"(?<![A-Za-z])" + _AUX_CONJ[lower] + r"(?![A-Za-z])"
        can_inflect_first = (
            part_index == 0
            and lower not in _NON_VERB_FIRST_PARTS
            and parts[-1].lower() in _PARTICLES
        )
        forms = _verb_forms(part) if can_inflect_first else [lower]
        return _word_boundary_pattern(forms)

    def _find_matches_in(segment: str, offset: int) -> set[tuple[int, int]]:
        """Run position matching on one text segment, return global-offset spans."""
        part_positions: list[list[tuple[int, int]]] = []
        for part_index, part in enumerate(parts):
            pat = _pattern_for(part, part_index)
            part_positions.append([(m.start(), m.end()) for m in re.finditer(pat, segment, re.IGNORECASE)])

        if not all(part_positions):
            return set()

        def _words_between(end_a: int, start_b: int) -> int:
            between = segment[end_a:start_b].strip()
            return len(between.split()) if between else 0

        _PART_BOUNDARY = re.compile(
            r'[.!?;:]|,\s*|\b(?:while|and|but|or|although|because|if|when|where|'
            r'after|before|once|since|unless|until|whether)\b',
            re.IGNORECASE,
        )

        def _has_part_boundary(end_a: int, start_b: int) -> bool:
            return bool(_PART_BOUNDARY.search(segment[end_a:start_b]))

        def _total_gap(chain: list[tuple[int, int]]) -> int:
            return sum(_words_between(chain[i][1], chain[i + 1][0]) for i in range(len(chain) - 1))

        consumed: set[tuple[int, int]] = set()
        raw_matches: list[list[tuple[int, int]]] = []

        for first_idx, first_pos in enumerate(part_positions[0]):
            if (0, first_idx) in consumed:
                continue

            chain = [first_pos]
            cursor = first_pos[1]
            chain_indices = [first_idx]
            ok = True

            for pi in range(1, len(parts)):
                best_cand = None
                best_gap = max_word_gap + 1
                best_ci = -1

                for ci, cand in enumerate(part_positions[pi]):
                    if (pi, ci) in consumed:
                        continue
                    if cand[0] < cursor:
                        continue
                    if _has_part_boundary(cursor, cand[0]):
                        continue
                    gap = _words_between(cursor, cand[0])
                    if gap < best_gap:
                        best_gap = gap
                        best_cand = cand
                        best_ci = ci

                if best_cand is None or best_gap > max_word_gap:
                    ok = False
                    break

                chain.append(best_cand)
                chain_indices.append(best_ci)
                cursor = best_cand[1]

            if not ok:
                continue

            raw_matches.append(chain)
            for pi, ci in enumerate(chain_indices):
                consumed.add((pi, ci))

        if not raw_matches:
            return set()

        # Two-level grouping:
        #   1) Sentence boundary (.?!) is always a hard break
        #   2) Clause boundary (subordinating conjunctions like while/and/but)
        #      also breaks groups — independent clause = independent phrase use
        #   3) Within a group, contiguous-priority filters false positives
        _SENTENCE_BREAK = re.compile(r'[.!?]+\s+')
        _CLAUSE_BREAK = re.compile(
            r'\b(?:while|and|but|or|although|because|if|when|where|'
            r'after|before|once|since|unless|until|whether)\b\s+',
            re.IGNORECASE,
        )

        def _is_group_break(prev_end: int, curr_start: int) -> bool:
            between = segment[prev_end:curr_start]
            if _SENTENCE_BREAK.search(between):
                return True
            if _CLAUSE_BREAK.search(between):
                return True
            return False

        sorted_matches = sorted(raw_matches, key=lambda c: c[0][0])
        groups: list[list[list[tuple[int, int]]]] = [[sorted_matches[0]]]

        for j in range(1, len(sorted_matches)):
            prev_end = groups[-1][-1][-1][1]
            curr_start = sorted_matches[j][0][0]
            if _is_group_break(prev_end, curr_start):
                groups.append([sorted_matches[j]])
            else:
                groups[-1].append(sorted_matches[j])

        kept: list[list[tuple[int, int]]] = []
        for grp in groups:
            has_ctg = any(_total_gap(m) == 0 for m in grp)
            if has_ctg:
                kept.extend(m for m in grp if _total_gap(m) == 0)
            else:
                kept.extend(grp)

        spans: set[tuple[int, int]] = set()
        for chain in kept:
            if _total_gap(chain) == 0:
                spans.add((chain[0][0] + offset, chain[-1][1] + offset))
            else:
                for s, e in chain:
                    spans.add((s + offset, e + offset))
        return spans

    all_bold_spans = _find_matches_in(text, 0)

    if not all_bold_spans:
        return text

    # Build result with ** markers
    result_chars = []
    pos = 0
    while pos < len(text):
        matched = None
        for bs, be in sorted(all_bold_spans):
            if pos == bs:
                matched = (bs, be)
                break
        if matched:
            result_chars.append("**")
            result_chars.append(text[matched[0]:matched[1]])
            result_chars.append("**")
            pos = matched[1]
        else:
            result_chars.append(text[pos])
            pos += 1

    return "".join(result_chars)


def format_validated_card_en_zh(result: dict[str, Any]) -> str:
    word = result.get("word", "")
    senses = result.get("senses", [])

    if not senses and "definitions" in result:
        senses = [{"pos": result.get("pos", ""), "definition": d} for i, d in enumerate((result.get("definitions") or [])[:3]) if d]

    if not senses:
        return f"**{word}**"

    lines = [f"**{word}**"]

    phonetic = senses[0].get("phonetic", "")
    if phonetic:
        lines.append(f"\n🔤 {phonetic}\n")

    pos = senses[0].get("pos", "")

    # Merge definitions, deduplicate at granularity level
    seen_units: set[str] = set()
    def_units: list[str] = []
    for s in senses[:8]:
        d = s.get("definition", "")
        if not d:
            continue
        cleaned = _clean_def_text(d)
        if not cleaned:
            continue
        for unit in re.split(r'[；;]', cleaned):
            unit = unit.strip()
            if unit and unit not in seen_units:
                seen_units.add(unit)
                def_units.append(unit)
    defs_merged = "；".join(def_units[:6])
    if defs_merged:
        if pos:
            lines.append(f"- 🇨🇳 释义：{pos} {defs_merged}")
        else:
            lines.append(f"- 🇨🇳 释义：{defs_merged}")

    # Collect examples, deduplicate, bold target word
    examples_seen: set[str] = set()
    all_examples: list[str] = []
    for s in senses[:8]:
        ex = s.get("example", "") or ""
        if isinstance(ex, dict):
            en = ex.get("en", "")
            zh = ex.get("zh", "")
            ex = f"{en}（{zh}）" if en and zh else en or zh or ""
        if ex and ex not in examples_seen:
            ex_bolded = _bold_word_in_text(word, ex)
            examples_seen.add(ex)
            all_examples.append(ex_bolded)
    if all_examples:
        lines.append(f"- 💬 例句：{' '.join(all_examples[:3])}")

    return "\n".join(lines)


def format_validated_card_zh_en(result: dict[str, Any]) -> str:
    query = result.get("query", "")
    matches = result.get("matches", [])

    if not matches:
        return f"**{query}**"

    lines = [f"**{query}**"]
    first = matches[0]
    w1 = first.get("word", "")
    lines.append(f"- 🔤 最常用英文：{w1}")

    if len(matches) > 1:
        w2 = matches[1].get("word", "")
        lines.append(f"- 🔤 第二常用英文：{w2}")

    defs = first.get("definitions") or []
    if defs:
        pos = first.get("pos", "")
        defn = defs[0]
        if pos and defn:
            lines.append(f"- 🇨🇳 对应义：{pos} {defn}")
        elif defn:
            lines.append(f"- 🇨🇳 对应义：{defn}")

    example = first.get("example", "")
    if example:
        lines.append(f"- 💬 例句：{example}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local dictionary lookup")
    parser.add_argument("--mode", required=True, choices=("en_to_zh", "zh_to_en"))
    parser.add_argument("query", help="Word or phrase to look up")
    parser.add_argument("--data-dir", default=None, help="Directory with dictionary assets")
    parser.add_argument("--db", default=None, help="Path to dictionary.db")
    parser.add_argument("--sample", default=None, help="Path to sample_dictionary.json")
    parser.add_argument("--format", default="json", choices=("json", "text"), help="Output format")
    args = parser.parse_args()

    data_dir = resolve_path(args.data_dir, "SELF_LEARNING_TUTOR_DATA_DIR", ROOT / "data")
    db_path = resolve_path(args.db, "SELF_LEARNING_TUTOR_DB", data_dir / "dictionary.db")
    sample_path = resolve_path(args.sample, "SELF_LEARNING_TUTOR_SAMPLE", data_dir / "sample_dictionary.json")

    sample_indexes = load_sample_indexes(sample_path)

    if args.mode == "en_to_zh":
        result = lookup_en_to_zh(args.query, db_path, sample_indexes)
    else:
        result = lookup_zh_to_en(args.query, db_path, sample_indexes)

    if result.get("error") == "not_found":
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 4

    if args.format == "text":
        if args.mode == "en_to_zh":
            print(format_validated_card_en_zh(result))
        else:
            print(format_validated_card_zh_en(result))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
