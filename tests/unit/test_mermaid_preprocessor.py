"""
Unit tests for Mermaid Diagram Preprocessor

Tests:
- Basic preprocessing
- Markdown element removal
- Sequence diagram syntax fixes
- Arrow syntax fixes
- Bracket cleaning
- Comma removal
- Aggressive cleanup mode
- Block extraction from Markdown
- Syntax validation
- Statistics generation
"""

import unittest
from api.tools.mermaid_preprocessor import MermaidPreprocessor


class TestMermaidPreprocessor(unittest.TestCase):
    """Test MermaidPreprocessor functionality"""

    def test_preprocess_empty_input(self):
        """Test preprocessing with empty input"""
        result = MermaidPreprocessor.preprocess("")
        self.assertEqual(result, "")

        result = MermaidPreprocessor.preprocess("   ")
        self.assertEqual(result, "")

    def test_preprocess_clean_code(self):
        """Test preprocessing with clean Mermaid code"""
        clean_code = """graph TD
    A[Start] --> B[Process]
    B --> C[End]"""

        result = MermaidPreprocessor.preprocess(clean_code)
        self.assertIn("A[Start]", result)
        self.assertIn("B[Process]", result)
        self.assertIn("C[End]", result)

    def test_remove_markdown_links(self):
        """Test removal of Markdown links"""
        code = """graph TD
    A[Click [here](http://example.com) for more] --> B"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertNotIn("](", result)
        self.assertIn("here", result)  # Link text should remain

    def test_remove_sources_references(self):
        """Test removal of Sources references"""
        code = """graph TD
    A[Start] --> B[End]
Sources: [file.py](http://example.com)"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertNotIn("Sources:", result)

    def test_remove_markdown_formatting(self):
        """Test removal of Markdown formatting"""
        code = """graph TD
    A[**Bold** text] --> B[*italic* text]
    C[`code` block]"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertNotIn("**", result)
        self.assertNotIn("*", result)
        self.assertNotIn("`", result)
        self.assertIn("Bold", result)
        self.assertIn("italic", result)

    def test_fix_sequence_diagram_autonumber(self):
        """Test fixing autonumber syntax errors"""
        code = """sequenceDiagram
    autonumber , [Error]
    Alice->>Bob: Hello"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertIn("autonumber", result)
        self.assertNotIn(", [Error]", result)

    def test_fix_sequence_diagram_participant(self):
        """Test fixing participant syntax errors"""
        code = """sequenceDiagram
    participant Alice , [Error]
    Alice->>Bob: Hi"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertIn("participant Alice", result)
        self.assertNotIn(", [Error]", result)

    def test_fix_arrow_with_comma(self):
        """Test fixing arrow syntax with comma"""
        code = """sequenceDiagram
    Alice->>Bob: Message, [Error]
    Bob->>Alice: Reply"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertIn("Alice->>Bob: Message", result)
        # Should remove the trailing comma and bracket content

    def test_fix_comma_before_arrow(self):
        """Test fixing comma before arrow"""
        code = """graph TD
    A , --> B"""

        result = MermaidPreprocessor.preprocess(code)
        self.assertNotIn(", -->", result)
        self.assertIn("A-->", result) or self.assertIn("A -->", result)

    def test_fix_flowchart_node_comma(self):
        """Test fixing flowchart node definition with comma"""
        code = """graph TD
    A[Node Label] ,
    B[Another]"""

        result = MermaidPreprocessor.preprocess(code)
        # Should remove trailing comma
        self.assertNotIn("] ,", result)

    def test_clean_isolated_brackets(self):
        """Test cleaning isolated brackets"""
        code = """graph TD
    A[Start]
    [Isolated]
    B[End]"""

        result = MermaidPreprocessor.preprocess(code)
        # Isolated bracket line should be removed
        lines = result.split('\n')
        self.assertTrue(all('[Isolated]' not in line or 'A[Start]' in line or 'B[End]' in line for line in lines))

    def test_remove_trailing_commas(self):
        """Test removal of trailing commas"""
        code = """graph TD
    A[Start] ,
    B[End] ,"""

        result = MermaidPreprocessor.preprocess(code)
        # Should not end lines with commas
        for line in result.split('\n'):
            self.assertFalse(line.strip().endswith(','))

    def test_remove_leading_commas(self):
        """Test removal of leading commas"""
        code = """graph TD
    A[Start]
    , B[End]"""

        result = MermaidPreprocessor.preprocess(code)
        # Should not start lines with commas
        for line in result.split('\n'):
            self.assertFalse(line.strip().startswith(','))

    def test_clean_formatting_whitespace(self):
        """Test whitespace and formatting cleanup"""
        code = """graph TD
    A[Start]    -->    B[End]


    C[Another]"""

        result = MermaidPreprocessor.preprocess(code)
        # Should normalize whitespace
        self.assertNotIn("    -->    ", result)
        # Should limit consecutive empty lines
        self.assertNotIn("\n\n\n", result)

    def test_aggressive_cleanup(self):
        """Test aggressive cleanup mode"""
        code = """graph TD
    A[Start [nested]] --> B[End, [error]]"""

        result = MermaidPreprocessor.preprocess(code, aggressive=True)
        # Aggressive mode removes all brackets
        self.assertNotIn("[", result)
        self.assertNotIn("]", result)

    def test_extract_and_process_mermaid_blocks(self):
        """Test extracting and processing Mermaid blocks from Markdown"""
        markdown = """# Documentation

Some text here.

```mermaid
graph TD
    A[Start] , [Error]
    B[End]
```

More text.

```mermaid
sequenceDiagram
    autonumber , [Error]
    Alice->>Bob: Hi
```

End of document."""

        result = MermaidPreprocessor.extract_and_process_mermaid_blocks(markdown)

        # Should preserve Markdown structure
        self.assertIn("# Documentation", result)
        self.assertIn("Some text here", result)
        self.assertIn("```mermaid", result)

        # Should clean Mermaid code
        self.assertNotIn(", [Error]", result)

    def test_extract_no_mermaid_blocks(self):
        """Test processing Markdown with no Mermaid blocks"""
        markdown = """# Documentation

Regular content without diagrams."""

        result = MermaidPreprocessor.extract_and_process_mermaid_blocks(markdown)
        self.assertEqual(result, markdown)

    def test_validate_syntax_clean_code(self):
        """Test syntax validation with clean code"""
        code = """graph TD
    A[Start] --> B[End]"""

        is_valid, errors = MermaidPreprocessor.validate_syntax(code)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_syntax_trailing_commas(self):
        """Test syntax validation detects trailing commas"""
        code = """graph TD
    A[Start] ,
    B[End]"""

        is_valid, errors = MermaidPreprocessor.validate_syntax(code)
        self.assertFalse(is_valid)
        self.assertTrue(any("Trailing comma" in error for error in errors))

    def test_validate_syntax_comma_before_bracket(self):
        """Test syntax validation detects comma before bracket"""
        code = """graph TD
    A[Start] , [Error]"""

        is_valid, errors = MermaidPreprocessor.validate_syntax(code)
        self.assertFalse(is_valid)
        self.assertTrue(any("Comma before bracket" in error for error in errors))

    def test_validate_syntax_isolated_bracket(self):
        """Test syntax validation detects isolated brackets"""
        code = """graph TD
    A[Start]
    [Isolated"""

        is_valid, errors = MermaidPreprocessor.validate_syntax(code)
        self.assertFalse(is_valid)
        self.assertTrue(any("Isolated left bracket" in error for error in errors))

    def test_validate_syntax_empty_code(self):
        """Test syntax validation with empty code"""
        is_valid, errors = MermaidPreprocessor.validate_syntax("")
        self.assertFalse(is_valid)
        self.assertTrue(any("Empty Mermaid code" in error for error in errors))

    def test_get_statistics_flowchart(self):
        """Test statistics for flowchart diagram"""
        code = """graph TD
    A --> B
    B --> C"""

        stats = MermaidPreprocessor.get_statistics(code)
        self.assertEqual(stats['line_count'], 3)
        self.assertEqual(stats['diagram_type'], 'flowchart')
        self.assertFalse(stats['has_errors'])
        self.assertEqual(stats['error_count'], 0)

    def test_get_statistics_sequence_diagram(self):
        """Test statistics for sequence diagram"""
        code = """sequenceDiagram
    Alice->>Bob: Hello
    Bob->>Alice: Hi"""

        stats = MermaidPreprocessor.get_statistics(code)
        self.assertEqual(stats['diagram_type'], 'sequence')
        self.assertFalse(stats['has_errors'])

    def test_get_statistics_with_errors(self):
        """Test statistics for diagram with errors"""
        code = """graph TD
    A[Start] ,
    B[End] , [Error]"""

        stats = MermaidPreprocessor.get_statistics(code)
        self.assertTrue(stats['has_errors'])
        self.assertGreater(stats['error_count'], 0)
        self.assertIsInstance(stats['errors'], list)

    def test_get_statistics_empty_code(self):
        """Test statistics for empty code"""
        stats = MermaidPreprocessor.get_statistics("")
        self.assertEqual(stats['line_count'], 0)
        self.assertEqual(stats['char_count'], 0)
        self.assertIsNone(stats['diagram_type'])
        self.assertFalse(stats['has_errors'])

    def test_complex_sequence_diagram_cleanup(self):
        """Test complex sequence diagram with multiple errors"""
        code = """sequenceDiagram
    autonumber , [Error]
    participant Alice , [Error]
    participant Bob as **Bob Smith**

    Alice->>Bob: Hello [link](http://example.com), [Error]
    activate Bob , [Error]
    Bob->>Alice: Hi there
    deactivate Bob , [Error]

    Note over Alice,Bob: Sources: [file.py](http://example.com)"""

        result = MermaidPreprocessor.preprocess(code)

        # Should remove all error patterns
        self.assertNotIn(", [Error]", result)
        self.assertNotIn("**", result)
        self.assertNotIn("[link](", result)
        self.assertNotIn("Sources:", result)

        # Should preserve valid elements
        self.assertIn("autonumber", result)
        self.assertIn("participant Alice", result)
        self.assertIn("participant Bob", result)
        self.assertIn("activate Bob", result)
        self.assertIn("deactivate Bob", result)

    def test_complex_flowchart_cleanup(self):
        """Test complex flowchart with multiple errors"""
        code = """graph TD
    A[**Start**] , [Error]
    B[Process [link](http://example.com)]
    C{`Decision`}

    A , --> B
    B --> C
    C -->|Yes| D[End] ,
    C -->|No| E[*Retry*]

    Sources: [README.md](http://example.com)"""

        result = MermaidPreprocessor.preprocess(code)

        # Should clean all errors
        self.assertNotIn(", [Error]", result)
        self.assertNotIn("**", result)
        self.assertNotIn("`", result)
        self.assertNotIn("*Retry*", result)
        self.assertNotIn("[link](", result)
        self.assertNotIn("Sources:", result)
        self.assertNotIn(", -->", result)

        # Should preserve structure
        self.assertIn("A[", result)
        self.assertIn("Start", result)
        self.assertIn("Decision", result)

    def test_preserve_valid_brackets_in_labels(self):
        """Test that valid brackets in labels are preserved"""
        code = """graph TD
    A[Array[0]] --> B[Map[key]]
    C[Object{prop}]"""

        result = MermaidPreprocessor.preprocess(code)

        # Should preserve node definitions
        self.assertIn("A[", result)
        self.assertIn("B[", result)
        self.assertIn("C[", result)

    def test_unicode_and_chinese_content(self):
        """Test preprocessing with Unicode and Chinese characters"""
        code = """graph TD
    A[开始 **Start**] , [错误]
    B[处理数据]
    A --> B

    Sources: [文档](http://example.com)"""

        result = MermaidPreprocessor.preprocess(code)

        # Should preserve Chinese characters
        self.assertIn("开始", result)
        self.assertIn("处理数据", result)

        # Should remove errors and formatting
        self.assertNotIn("**", result)
        self.assertNotIn(", [错误]", result)
        self.assertNotIn("Sources:", result)


if __name__ == '__main__':
    unittest.main()
