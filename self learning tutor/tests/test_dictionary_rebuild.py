#!/usr/bin/env python3
"""Regression tests for dictionary schema removal and rebuild completeness."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import build_cambridge_dict as bcd  # noqa: E402
except ImportError:
    bcd = None  # type: ignore[assignment]

try:
    import migrate_phrases_to_db as mpdb  # noqa: E402
except ImportError:
    mpdb = None  # type: ignore[assignment]


class TestBuildCambridgeSchema:
    def test_schema_drops_definition_column(self):
        if bcd is None:
            pytest.skip("build_cambridge_dict not importable")
        conn = sqlite3.connect(":memory:")
        try:
            bcd.ensure_schema(conn)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(dictionary)")}
            assert "definition" not in columns
            assert "definitions" in columns
        finally:
            conn.close()

    def test_already_fetched_requires_real_definitions(self):
        if bcd is None:
            pytest.skip("build_cambridge_dict not importable")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            bcd.ensure_schema(conn)
            conn.execute(
                "INSERT INTO dictionary (word, source, definitions) VALUES (?, 'cambridge', ?)",
                ("setup", "[]"),
            )
            assert not bcd.already_fetched(conn, "setup")
            conn.execute(
                "UPDATE dictionary SET definitions = ? WHERE word = ?",
                ('["结构；安排"]', "setup"),
            )
            assert bcd.already_fetched(conn, "setup")
        finally:
            conn.close()

    def test_fallback_html_populates_definitions(self):
        if bcd is None:
            pytest.skip("build_cambridge_dict not importable")
        html = """
        <html><body>
          <div class="entry-body">
            <span class="hw">setup</span>
            <span class="uk"><span class="pron">/ˈset.ʌp/</span></span>
            <div class="def">the way something is arranged</div>
            <div class="trans">结构；安排；设置</div>
            <div class="examp dexamp">The setup was easy.</div>
          </div>
        </body></html>
        """
        entry = bcd.extract_entry(html, "setup", "https://example.com")
        assert entry is not None
        assert entry.definitions
        assert any("结构" in item for item in entry.definitions)


class TestMigratePhrasesSchema:
    def test_schema_drops_definition_column(self):
        if mpdb is None:
            pytest.skip("migrate_phrases_to_db not importable")
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dictionary.db"
            phrases_path = Path(tmpdir) / "gaokao_phrases.json"
            phrases_path.write_text(
                json.dumps(
                    {
                        "phrases": [
                            {
                                "phrase": "in the future",
                                "definitions": ["将来；未来"],
                                "examples": [{"en": "We will talk in the future.", "zh": "我们以后再谈。"}],
                                "frequency": 4,
                                "zh_terms": ["将来"],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "utf-8",
            )
            mpdb.migrate(db_path, phrases_path, dry_run=False)
            conn = sqlite3.connect(str(db_path))
            try:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(dictionary)")}
                assert "definition" not in columns
                assert "definitions" in columns
                row = conn.execute("SELECT word, definitions FROM dictionary WHERE word = ?", ("in the future",)).fetchone()
                assert row is not None
                assert row[0] == "in the future"
                assert row[1] and "将来" in row[1]
            finally:
                conn.close()

    def test_refreshes_existing_empty_definition_rows(self):
        if mpdb is None:
            pytest.skip("migrate_phrases_to_db not importable")
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dictionary.db"
            phrases_path = Path(tmpdir) / "gaokao_phrases.json"
            phrases_path.write_text(
                json.dumps(
                    {
                        "phrases": [
                            {
                                "phrase": "take part in",
                                "definitions": ["参加；参与"],
                                "examples": [{"en": "She took part in the game.", "zh": "她参加了比赛。"}],
                                "frequency": 4,
                                "zh_terms": ["参加"],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "utf-8",
            )
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE dictionary (
                        word TEXT PRIMARY KEY,
                        phonetic TEXT,
                        phonetic_uk TEXT,
                        phonetic_us TEXT,
                        translation TEXT,
                        definitions TEXT DEFAULT '[]',
                        idioms TEXT DEFAULT '[]',
                        collocations TEXT DEFAULT '[]',
                        collins INTEGER DEFAULT 0,
                        oxford INTEGER DEFAULT 0,
                        tag TEXT,
                        bnc INTEGER DEFAULT 0,
                        frq INTEGER DEFAULT 0,
                        frequency INTEGER DEFAULT 0,
                        exchange TEXT,
                        detail TEXT,
                        audio TEXT,
                        example TEXT,
                        example_source TEXT,
                        example_url TEXT,
                        source TEXT DEFAULT '',
                        updated_at TEXT,
                        cefr_level TEXT DEFAULT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO dictionary (word, source, definitions, example, idioms, collocations) VALUES (?, '', '[]', ?, ?, ?)",
                    (
                        "take part in",
                        json.dumps([{"en": "old example", "zh": "旧例句"}], ensure_ascii=False),
                        json.dumps([{"zh": "旧习语"}], ensure_ascii=False),
                        json.dumps([{"zh": "旧搭配"}], ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            mpdb.migrate(db_path, phrases_path, dry_run=False)

            conn = sqlite3.connect(str(db_path))
            try:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT source, definitions, example, idioms, collocations FROM dictionary WHERE word = ?", ("take part in",)).fetchone()
                assert row is not None
                assert row["source"] == "gaokao_phrases"
                assert row["definitions"] and "参加" in row["definitions"]
                assert row["example"] and "She took part in the game." in row["example"]
                assert row["idioms"] == json.dumps([{"zh": "旧习语"}], ensure_ascii=False)
                assert row["collocations"] == json.dumps([{"zh": "旧搭配"}], ensure_ascii=False)
            finally:
                conn.close()
