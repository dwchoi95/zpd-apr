import unittest

from src.core.retention import retention


class RetentionTest(unittest.TestCase):
    def test_python_counts_source_tokens_and_nonblank_lines(self) -> None:
        self.assertEqual(
            retention("a = 1\nprint(a)\n", "a = 1\n\nprint(a + 1)\n"),
            {"token_retention": 1.0, "line_retention": 0.5},
        )

    def test_java_counts_word_and_symbol_tokens(self) -> None:
        self.assertEqual(
            retention("int x = 1;\nreturn x;", "int x = 2;\nreturn x;", language="java"),
            {"token_retention": 7 / 8, "line_retention": 0.5},
        )

    def test_unparsable_python_falls_back_to_whitespace_tokens(self) -> None:
        self.assertEqual(retention("if x:\n  y(", "if x:\n  y(")["token_retention"], 1.0)

    def test_empty_source_keeps_everything_only_when_candidate_is_empty(self) -> None:
        self.assertEqual(retention("", ""), {"token_retention": 1.0, "line_retention": 1.0})
        self.assertEqual(retention("", "x")["token_retention"], 0.0)


if __name__ == "__main__":
    unittest.main()
