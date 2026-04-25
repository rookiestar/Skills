import pathlib
import sqlite3
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backfill_dictionary_pos import backfill_missing_pos
from scripts.dictionary_utils import extract_pos_from_text, record_to_entry


class DictionaryUtilsTests(unittest.TestCase):
    def test_extract_pos_from_text_handles_common_prefixes(self) -> None:
        self.assertEqual(extract_pos_from_text("n. a thin cylindrical pointed writing implement"), "n.")
        self.assertEqual(extract_pos_from_text("adj. / n. useful for many purposes"), "adj. / n.")
        self.assertEqual(extract_pos_from_text("  vt. to make clear"), "vt.")

    def test_record_to_entry_infers_pos_from_definition(self) -> None:
        entry = record_to_entry(
            {
                "word": "clearance",
                "pos": "",
                "definition": "n. the process of making a place clear",
                "translation": "n. 清除；间隙",
                "example": "",
                "sentence": "The road was reopened after clearance.",
            }
        )

        self.assertEqual(entry["pos"], "n.")
        self.assertEqual(entry["definitions"], ["清除", "间隙"])
        self.assertEqual(entry["example"], "The road was reopened after clearance.")

    def test_record_to_entry_prefers_explicit_pos(self) -> None:
        entry = record_to_entry(
            {
                "word": "clearance",
                "pos": "n.",
                "definition": "v. to clear away",
                "translation": "n. 清除",
            }
        )

        self.assertEqual(entry["pos"], "n.")

    def test_record_to_entry_uses_translation_when_definition_lacks_pos(self) -> None:
        entry = record_to_entry(
            {
                "word": "clearance",
                "definition": "the process of clearing",
                "translation": "adj. 清晰的",
            }
        )

        self.assertEqual(entry["pos"], "adj.")
        self.assertEqual(entry["definitions"], ["清晰的"])

    def test_backfill_missing_pos_updates_database_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "dictionary.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE dictionary (
                        word TEXT,
                        pos TEXT,
                        definition TEXT,
                        translation TEXT,
                        example TEXT,
                        sentence TEXT
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO dictionary (word, pos, definition, translation, example, sentence) VALUES (?, ?, ?, ?, ?, ?)",
                    ("clearance", "", "n. the process of making a place clear", "n. 清除", "", ""),
                )
                conn.commit()
            finally:
                conn.close()

            inspected, updated = backfill_missing_pos(db_path)
            self.assertEqual(inspected, 1)
            self.assertEqual(updated, 1)

            conn = sqlite3.connect(db_path)
            try:
                pos = conn.execute("SELECT pos FROM dictionary WHERE word = ?", ("clearance",)).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(pos, "n.")


if __name__ == "__main__":
    unittest.main()
