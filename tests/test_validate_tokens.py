from __future__ import annotations

import runpy
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = runpy.run_path(str(ROOT / "scripts" / "validate_tokens.py"))
CssSyntaxError = VALIDATOR["CssSyntaxError"]
strip_comments = VALIDATOR["strip_comments"]


class StripCommentsTests(unittest.TestCase):
    def test_strips_valid_comments(self) -> None:
        css = ":root { /* palette */ --gt-navy: #0B1F3A; }"
        self.assertEqual(strip_comments(css), ":root {  --gt-navy: #0B1F3A; }")

    def test_preserves_comment_markers_inside_quoted_values(self) -> None:
        css = ':root { --example: "/* literal */"; /* real */ --space-1: 4px; }'
        expected = ':root { --example: "/* literal */";  --space-1: 4px; }'
        self.assertEqual(strip_comments(css), expected)

    def test_rejects_many_unterminated_comment_openers(self) -> None:
        crafted_css = ":root { --space-1: 4px; }" + "/*x" * 5_000
        with self.assertRaisesRegex(CssSyntaxError, "unterminated CSS comment"):
            strip_comments(crafted_css)


if __name__ == "__main__":
    unittest.main()
