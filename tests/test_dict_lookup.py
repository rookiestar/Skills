from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class DictLookupTests(unittest.TestCase):
    def run_lookup(self, *args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "dict_lookup.py"), *args],
            cwd=str(cwd or ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_en_to_zh_uses_sample_data(self) -> None:
        sample_path = ROOT / "data" / "sample_dictionary.json"
        result = self.run_lookup(
            "--mode",
            "en_to_zh",
            "--db",
            str(ROOT / "tmp" / "no-such-dictionary.db"),
            "--sample",
            str(sample_path),
            "architecture",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["word"], "architecture")
        self.assertEqual(payload["definitions"][0], "建筑学")
        self.assertTrue(payload["example"])

    def test_zh_to_en_uses_sample_data(self) -> None:
        sample_path = ROOT / "data" / "sample_dictionary.json"
        result = self.run_lookup(
            "--mode",
            "zh_to_en",
            "--db",
            str(ROOT / "tmp" / "no-such-dictionary.db"),
            "--sample",
            str(sample_path),
            "重要的",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["query"], "重要的")
        self.assertGreaterEqual(len(payload["matches"]), 2)
        self.assertEqual(payload["matches"][0]["word"], "important")
        self.assertEqual(payload["matches"][1]["word"], "significant")

    def test_missing_lookup_logs_the_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            result = self.run_lookup(
                "--mode",
                "en_to_zh",
                "--data-dir",
                str(data_dir),
                "unlistedterm",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not_found", result.stderr)
            log_path = data_dir / "missing_words.log"
            self.assertTrue(log_path.exists())
            self.assertEqual(log_path.read_text(encoding="utf-8").strip(), "unlistedterm")


if __name__ == "__main__":
    unittest.main()
