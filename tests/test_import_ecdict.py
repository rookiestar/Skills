from __future__ import annotations

import json
import csv
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ImportEcdictTests(unittest.TestCase):
    def test_import_sqlite_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            source_db = tmp_path / "source.db"
            dest_db = tmp_path / "dictionary.db"

            conn = sqlite3.connect(source_db)
            try:
                conn.execute(
                    """
                    CREATE TABLE stardict (
                        word TEXT PRIMARY KEY,
                        pos TEXT,
                        phonetic TEXT,
                        translation TEXT,
                        example TEXT,
                        frequency INTEGER
                    )
                    """
                )
                conn.executemany(
                    "INSERT INTO stardict (word, pos, phonetic, translation, example, frequency) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        ("apple", "n.", "/ˈæpəl/", "n. 苹果", "I eat an apple after lunch.", 1200),
                        ("important", "adj.", "/ɪmˈpɔːrtnt/", "adj. 重要的; 有意义的", "It is important to finish your homework on time.", 1300),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "import_ecdict.py"),
                    "--source",
                    str(source_db),
                    "--dest",
                    str(dest_db),
                ],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(dest_db.exists(), "destination db was not created")

            conn = sqlite3.connect(dest_db)
            conn.row_factory = sqlite3.Row
            try:
                apple = conn.execute("SELECT * FROM dictionary WHERE word = 'apple'").fetchone()
                self.assertIsNotNone(apple)
                apple_defs = json.loads(apple["definitions"])
                self.assertEqual(apple_defs[0], "苹果")
                reverse = conn.execute(
                    "SELECT word FROM dictionary_reverse WHERE zh_term = '重要的' ORDER BY word"
                ).fetchall()
                self.assertGreaterEqual(len(reverse), 1)
                self.assertEqual(reverse[0]["word"], "important")
            finally:
                conn.close()

    def test_import_csv_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            source_csv = tmp_path / "ecdict.csv"
            dest_db = tmp_path / "dictionary.db"

            with source_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "word",
                        "phonetic",
                        "definition",
                        "translation",
                        "pos",
                        "collins",
                        "oxford",
                        "tag",
                        "bnc",
                        "frq",
                        "exchange",
                        "detail",
                        "audio",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "word": "apple",
                        "phonetic": "/ˈæpəl/",
                        "definition": "",
                        "translation": "n. 苹果",
                        "pos": "n.",
                        "collins": "1",
                        "oxford": "1",
                        "tag": "zk",
                        "bnc": "10",
                        "frq": "20",
                        "exchange": "",
                        "detail": "",
                        "audio": "",
                    }
                )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "import_ecdict.py"),
                    "--source",
                    str(source_csv),
                    "--dest",
                    str(dest_db),
                ],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            conn = sqlite3.connect(dest_db)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute("SELECT * FROM dictionary WHERE word = 'apple'").fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["translation"], "n. 苹果")
                reverse = conn.execute(
                    "SELECT word FROM dictionary_reverse WHERE zh_term = '苹果'"
                ).fetchone()
                self.assertIsNotNone(reverse)
                self.assertEqual(reverse["word"], "apple")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
