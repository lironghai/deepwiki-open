"""
Unit tests for agent_tools hybrid retrieval (grep pre-prompt).

Tests:
- _grep_pattern_from_query: pattern derivation from user query
- format_grep_context_for_prompt: raw grep output -> context block
- grep_for_query: integration with mocked grep execution
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from api.tools.agent_tools import (
    GREP_PREPROMPT_MAX_RESULTS,
    _grep_pattern_from_query,
    format_grep_context_for_prompt,
    grep_for_query,
)


class TestGrepPatternFromQuery(unittest.TestCase):
    """Test _grep_pattern_from_query pattern derivation."""

    def test_empty_or_whitespace_returns_none(self):
        self.assertIsNone(_grep_pattern_from_query(""))
        self.assertIsNone(_grep_pattern_from_query("   "))
        self.assertIsNone(_grep_pattern_from_query("\t\n"))

    def test_identifier_extracted_longest(self):
        # Longest code-like identifier wins
        pattern = _grep_pattern_from_query("where is prepare_retriever used")
        self.assertIn(pattern, ("prepare_retriever", "where"))  # both 5+ chars
        self.assertTrue(pattern.isidentifier() or pattern.replace("_", "").isalnum())

    def test_single_identifier(self):
        self.assertEqual(_grep_pattern_from_query("RAG"), "RAG")
        self.assertEqual(_grep_pattern_from_query("  get_model_config  "), "get_model_config")

    def test_fallback_escaped_prefix(self):
        # Query with no identifier (e.g. Chinese or symbols) -> escaped prefix
        q = "怎么用？"
        pattern = _grep_pattern_from_query(q)
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern, "怎么用？")  # re.escape of that

    def test_strips_whitespace(self):
        self.assertEqual(_grep_pattern_from_query("  run_agent_loop  "), "run_agent_loop")


class TestFormatGrepContextForPrompt(unittest.TestCase):
    """Test format_grep_context_for_prompt output formatting."""

    def test_empty_or_no_matches_returns_empty(self):
        self.assertEqual(format_grep_context_for_prompt(""), "")
        self.assertEqual(format_grep_context_for_prompt("No matches found."), "")
        self.assertEqual(format_grep_context_for_prompt("  No matches found.  "), "")
        self.assertEqual(format_grep_context_for_prompt("Error: Repository path not available"), "")

    def test_error_prefix_returns_empty(self):
        self.assertEqual(format_grep_context_for_prompt("Error: invalid pattern"), "")

    def test_single_file_single_line(self):
        raw = "api/main.py:1:from api.rag import RAG"
        out = format_grep_context_for_prompt(raw)
        self.assertIn("## Keyword matches (grep)", out)
        self.assertIn("## File Path: api/main.py", out)
        self.assertIn("  1: from api.rag import RAG", out)

    def test_single_file_multiple_lines(self):
        raw = "src/foo.ts:10:const x = 1;\nsrc/foo.ts:11:const y = 2;"
        out = format_grep_context_for_prompt(raw)
        self.assertIn("## File Path: src/foo.ts", out)
        self.assertIn("  10: const x = 1;", out)
        self.assertIn("  11: const y = 2;", out)

    def test_multiple_files_sorted_by_path(self):
        raw = "z.py:1:a\nb.py:2:c\na.py:3:d"
        out = format_grep_context_for_prompt(raw)
        self.assertIn("## Keyword matches (grep)", out)
        # Sorted: a.py, b.py, z.py
        pos_a = out.index("## File Path: a.py")
        pos_b = out.index("## File Path: b.py")
        pos_z = out.index("## File Path: z.py")
        self.assertLess(pos_a, pos_b)
        self.assertLess(pos_b, pos_z)

    def test_content_with_colon_preserved(self):
        raw = "api/config.py:20:BASE_URL = \"https://api.example.com\""
        out = format_grep_context_for_prompt(raw)
        self.assertIn("  20: BASE_URL = \"https://api.example.com\"", out)

    def test_path_with_colon_windows_style(self):
        # path could be like C:\repo\file.py:1:content (rsplit from right)
        raw = "C:\\repo\\file.py:1:content"
        out = format_grep_context_for_prompt(raw)
        self.assertIn("## File Path: C:\\repo\\file.py", out)
        self.assertIn("  1: content", out)

    def test_skips_malformed_lines(self):
        raw = "good/path.py:1:ok\nbadline\nanother/good.py:2:yes"
        out = format_grep_context_for_prompt(raw)
        self.assertIn("## File Path: good/path.py", out)
        self.assertIn("  1: ok", out)
        self.assertIn("## File Path: another/good.py", out)
        self.assertIn("  2: yes", out)


class TestGrepForQuery(unittest.TestCase):
    """Test grep_for_query with mocked execution."""

    def test_empty_query_returns_no_matches(self):
        self.assertEqual(grep_for_query("", "/some/path"), "No matches found.")
        self.assertEqual(grep_for_query("   ", "/some/path"), "No matches found.")

    def test_none_or_missing_repo_returns_no_matches(self):
        self.assertEqual(grep_for_query("RAG", None), "No matches found.")
        self.assertEqual(grep_for_query("RAG", ""), "No matches found.")

    def test_nonexistent_repo_path_returns_no_matches(self):
        self.assertEqual(
            grep_for_query("RAG", "/nonexistent/path/xyz"),
            "No matches found.",
        )

    @patch("api.tools.agent_tools._execute_grep_search")
    def test_calls_execute_with_derived_pattern_and_max_results(self, mock_execute):
        mock_execute.return_value = "api/rag.py:1:from api.rag import RAG"
        with tempfile.TemporaryDirectory() as tmp:
            result = grep_for_query("where is RAG used", tmp, max_results=15)
        self.assertEqual(result, "api/rag.py:1:from api.rag import RAG")
        mock_execute.assert_called_once()
        args = mock_execute.call_args[0][0]
        self.assertEqual(args["file_glob"], "*")
        self.assertEqual(args["max_results"], 15)
        self.assertIn(args["pattern"], ("where", "used", "RAG"))  # one of identifiers

    @patch("api.tools.agent_tools._execute_grep_search")
    def test_default_max_results(self, mock_execute):
        mock_execute.return_value = "No matches found."
        with tempfile.TemporaryDirectory() as tmp:
            grep_for_query("RAG", tmp)
        args = mock_execute.call_args[0][0]
        self.assertEqual(args["max_results"], GREP_PREPROMPT_MAX_RESULTS)

    @patch("api.tools.agent_tools._execute_grep_search")
    def test_full_flow_format_after_grep(self, mock_execute):
        mock_execute.return_value = "api/main.py:15:from api.rag import RAG\napi/rag.py:1:class RAG:"
        with tempfile.TemporaryDirectory() as tmp:
            raw = grep_for_query("RAG", tmp)
        block = format_grep_context_for_prompt(raw)
        self.assertIn("## Keyword matches (grep)", block)
        self.assertIn("## File Path: api/main.py", block)
        self.assertIn("## File Path: api/rag.py", block)
        self.assertIn("  15: from api.rag import RAG", block)
        self.assertIn("  1: class RAG:", block)


if __name__ == "__main__":
    unittest.main()
