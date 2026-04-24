from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_cambridge_examples import extract_example_from_html


class FetchCambridgeExamplesTests(unittest.TestCase):
    def test_extracts_main_example(self) -> None:
        html = """
        <html>
          <body>
            <div class="def-block ddef_block">
              <div class="def-body ddef_b">
                <div class="examp dexamp">
                  <span class="eg deg">to study architecture</span>
                  <span class="trans dtrans dtrans-se hdb break-cj" lang="zh-Hans">学习建筑学</span>
                </div>
              </div>
            </div>
          </body>
        </html>
        """
        example = extract_example_from_html(html)
        self.assertEqual(example, "to study architecture 学习建筑学")

    def test_extracts_more_examples_when_main_example_missing(self) -> None:
        html = """
        <html>
          <body>
            <div class="def-block ddef_block">
              <div class="daccord">
                <li class="eg dexamp">Modernist architecture tries to conquer nature instead of working with it.</li>
              </div>
            </div>
          </body>
        </html>
        """
        example = extract_example_from_html(html)
        self.assertEqual(example, "Modernist architecture tries to conquer nature instead of working with it.")


if __name__ == "__main__":
    unittest.main()
